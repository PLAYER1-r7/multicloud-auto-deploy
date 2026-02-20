import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings

router = APIRouter()
_TEMPLATES_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


def _base_path(request: Request, settings: Settings) -> str:
    if not settings.stage_name:
        return ""
    return f"/{settings.stage_name}"


def _template_context(request: Request, settings: Settings, **extra: Any) -> dict[str, Any]:
    # ローカル開発モードでは local_user クッキーがある場合のみログイン済み
    if getattr(settings, 'auth_disabled', False):
        local_user = request.cookies.get("local_user")
        logged_in = bool(local_user)
        username = local_user
    else:
        logged_in = bool(request.cookies.get("id_token")
                         or request.cookies.get("access_token"))
        username = None
    return {
        "request": request,
        "logged_in": logged_in,
        "username": username,
        "auth_disabled": getattr(settings, 'auth_disabled', False),
        "base_path": _base_path(request, settings),
        **extra,
    }


def _get_auth_urls(settings: Settings) -> tuple[str | None, str | None, str]:
    if settings.auth_provider == "azure":
        if not (settings.azure_tenant_id and settings.azure_client_id and settings.azure_redirect_uri):
            return None, None, "Azure AD"

        login_url = (
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/authorize"
            f"?client_id={settings.azure_client_id}"
            f"&response_type=id_token"
            f"&response_mode=fragment"
            f"&scope={settings.oidc_scope.replace(' ', '+')}"
            f"&redirect_uri={settings.azure_redirect_uri}"
            f"&nonce=12345"
        )
        logout_url = None
        if settings.azure_logout_uri:
            logout_url = (
                f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/logout"
                f"?post_logout_redirect_uri={settings.azure_logout_uri}"
            )
        return login_url, logout_url, "Azure AD"

    if settings.auth_provider == "firebase":
        # Firebase handles login on client side via SDK / Widget
        # We don't return a standard OAuth2 URL here.
        # The template will check provider_label or settings.auth_provider
        return "", "", "Firebase"

    if settings.auth_provider == "gcp":
        if not (settings.gcp_client_id and settings.gcp_redirect_uri):
            return None, None, "Google"
        login_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.gcp_client_id}"
            f"&response_type=token+id_token"
            f"&scope={settings.oidc_scope.replace(' ', '+')}"
            f"&redirect_uri={settings.gcp_redirect_uri}"
        )
        # GCP logout is just clearing cookies, or redirecting to Google logout if desired
        return login_url, settings.gcp_logout_uri or None, "Google"

    # Default: AWS Cognito
    if not (settings.cognito_domain and settings.cognito_client_id and settings.cognito_redirect_uri):
        return None, None, "Cognito"
    login_url = (
        f"https://{settings.cognito_domain}/login?client_id={settings.cognito_client_id}"
        f"&response_type=token&scope={settings.oidc_scope.replace(' ', '+')}"
        f"&redirect_uri={settings.cognito_redirect_uri}"
    )
    logout_url = None
    if settings.cognito_logout_uri:
        logout_url = (
            f"https://{settings.cognito_domain}/logout?client_id={settings.cognito_client_id}"
            f"&logout_uri={settings.cognito_logout_uri}"
        )
    return login_url, logout_url, "Cognito"


@router.get("/login", name="login")
def login(request: Request, settings: Settings = Depends(get_settings)):
    # ローカル開発モード: 擬似ログインページを表示
    if getattr(settings, 'auth_disabled', False):
        return templates.TemplateResponse(
            "login.html",
            _template_context(
                request,
                settings,
                api_base_url=settings.clean_api_base_url,
                login_url=None,
                logout_url=None,
                provider_label="Local",
            ),
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    login_url, logout_url, provider_label = _get_auth_urls(settings)
    return templates.TemplateResponse(
        "login.html",
        _template_context(
            request,
            settings,
            api_base_url=settings.clean_api_base_url,
            login_url=login_url,
            logout_url=logout_url,
            provider_label=provider_label,
            firebase_config={
                "apiKey": settings.firebase_api_key,
                "authDomain": settings.firebase_auth_domain,
                "projectId": settings.firebase_project_id,
                "appId": settings.firebase_app_id,
            } if settings.auth_provider == "firebase" else None
        ),
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.get("/auth/callback", name="callback")
def callback(request: Request, settings: Settings = Depends(get_settings)):
    base_path = _base_path(request, settings)
    return templates.TemplateResponse(
        "callback.html",
        _template_context(
            request,
            settings,
            session_url=f"{base_path}/session",
            profile_url=f"{base_path}/profile",
        ),
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post("/login", name="login_post")
async def login_post(request: Request, response: Response, settings: Settings = Depends(get_settings)):
    """ローカル開発モード用の擬似ログイン"""
    if not getattr(settings, 'auth_disabled', False):
        raise HTTPException(
            status_code=403, detail="Not available in production mode")

    form_data = await request.form()
    username = form_data.get("username", "").strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    # 英数字とハイフン、アンダースコアのみ許可
    if not all(c.isalnum() or c in "-_" for c in username):
        raise HTTPException(
            status_code=400, detail="Username can only contain alphanumeric characters, hyphens, and underscores")

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        "local_user",
        username,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=86400,  # 24時間
    )
    return response


@router.post("/session", name="session")
async def session(request: Request, response: Response):
    payload = await request.json()
    id_token = payload.get("id_token") or ""
    access_token = payload.get("access_token") or ""
    expires_in = payload.get("expires_in") or 3600

    if not (id_token or access_token):
        raise HTTPException(status_code=400, detail="token missing")

    secure_cookie = request.url.scheme == "https"
    cookie_kwargs = {
        "httponly": True,
        "secure": secure_cookie,
        "samesite": "lax",
        "path": "/",
        "max_age": int(expires_in),
    }
    if id_token:
        response.set_cookie("id_token", id_token, **cookie_kwargs)
    if access_token:
        response.set_cookie("access_token", access_token, **cookie_kwargs)
    return {"ok": True}


@router.get("/logout", name="logout")
def logout(settings: Settings = Depends(get_settings)):
    base_path = f"/{settings.stage_name}" if settings.stage_name else ""

    # Azure AD セッションも無効化するため logout URL へリダイレクト
    if settings.auth_provider == "azure" and settings.azure_tenant_id and settings.azure_client_id:
        post_logout = settings.azure_logout_uri or (
            f"{base_path}/" if base_path else "/")
        azure_logout = (
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={post_logout}"
        )
        redirect_url = azure_logout

    # Cognito セッションも無効化するため Cognito logout URL へリダイレクト
    elif (
        settings.cognito_domain
        and settings.cognito_client_id
        and settings.cognito_logout_uri
    ):
        cognito_logout = (
            f"https://{settings.cognito_domain}/logout"
            f"?client_id={settings.cognito_client_id}"
            f"&logout_uri={settings.cognito_logout_uri}"
        )
        redirect_url = cognito_logout

    # GCP / other: simple-sns トップへ
    else:
        redirect_url = f"{base_path}/" if base_path else "/"

    response = RedirectResponse(url=redirect_url)
    response.delete_cookie("id_token", path="/")
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("local_user", path="/")
    return response
