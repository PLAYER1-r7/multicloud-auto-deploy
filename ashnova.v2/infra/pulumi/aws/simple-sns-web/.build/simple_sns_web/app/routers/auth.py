from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _base_path(request: Request, settings: Settings) -> str:
    if not settings.stage_name:
        return ""
    return f"/{settings.stage_name}"


def _template_context(request: Request, settings: Settings, **extra: Any) -> dict[str, Any]:
    logged_in = bool(request.cookies.get("id_token")
                     or request.cookies.get("access_token"))
    return {
        "request": request,
        "logged_in": logged_in,
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
            f"&response_type=token+id_token"
            f"&response_mode=fragment"
            f"&scope={settings.oidc_scope.replace(' ', '+')}"
            f"&redirect_uri={settings.azure_redirect_uri}"
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
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("id_token", path="/")
    response.delete_cookie("access_token", path="/")
    return response
