from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as _Response
from fastapi.templating import Jinja2Templates
import requests

from app.config import Settings, get_settings
from app.routers.auth import _template_context, _get_auth_urls

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _auth_header(request: Request, settings: Settings | None = None) -> dict[str, str]:
    # ローカル開発モード: local_user クッキーからユーザー名を取得
    if settings and getattr(settings, 'auth_disabled', False):
        local_user = request.cookies.get("local_user")
        if local_user:
            return {"Authorization": f"Bearer local:{local_user}"}
        return {}

    access_token = request.cookies.get("access_token")
    id_token = request.cookies.get("id_token")
    token = id_token or access_token
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _fetch_json_with_headers(
    url: str, params: dict[str, Any] | None, headers: dict[str, str]
) -> Any:
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        res.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return res.json()


def _post_json_with_headers(
    url: str, payload: dict[str, Any], headers: dict[str, str]
) -> Any:
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if not res.ok:
            detail = res.text or res.reason or "Request failed"
            raise HTTPException(
                status_code=502,
                detail=f"{res.status_code} {res.reason}: {detail}",
            )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return res.json()


@router.get("/", name="home")
def home(request: Request, settings: Settings = Depends(get_settings)):
    error = None
    posts = []
    success = None
    tag_filter = request.query_params.get("tag")
    search_keyword = request.query_params.get("q")

    api_url = f"{settings.clean_api_base_url}/posts"

    try:
        params: dict[str, Any] = {"limit": 20}
        if tag_filter:
            params["tag"] = tag_filter

        # Public Endpoint? If posts are public, no auth header needed.
        # But if auth is optional, pass it if relevant?
        # Assuming posts are public for read in this simple sns.
        # But checks main.py: _fetch_json calls _fetch_json_with_headers with empty headers.
        # So it is public.

        headers = {}
        data = _fetch_json_with_headers(api_url, params, headers)
        posts = data.get("items", [])

        if search_keyword:
            needle = search_keyword.strip().lower()
            if needle:
                posts = [
                    item
                    for item in posts
                    if str(item.get("content") or "").lower().find(needle) >= 0
                ]
    except HTTPException as exc:
        error = exc.detail

    return templates.TemplateResponse(
        "home.html",
        _template_context(
            request,
            settings,
            posts=posts,
            error=error,
            success=success,
            tag_filter=tag_filter,
            search_keyword=search_keyword,
        ),
    )


@router.post("/posts", name="post_create")
async def post_create(request: Request, settings: Settings = Depends(get_settings)):
    error = None
    success = None
    posts = []

    form = await request.form()
    content = str(form.get("content") or "").strip()
    raw_tags = str(form.get("tags") or "").strip()
    raw_files = form.getlist("images") if hasattr(form, "getlist") else []
    files = [item for item in raw_files if getattr(item, "filename", "")]
    image_keys = form.getlist("image_keys") if hasattr(form, "getlist") else []
    allowed_content_types = {
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    }

    headers = _auth_header(request, settings)
    if not headers and not settings.auth_disabled:
        error = "Authentication required"
    elif not content:
        error = "Content is required"
    elif len(files) > 16:
        error = "Too many images (max 16)"
    else:
        tags = [tag for tag in raw_tags.split() if tag]
        payload: dict[str, Any] = {"content": content}
        if tags:
            payload["tags"] = tags
        if image_keys:
            payload["imageKeys"] = [key for key in image_keys if key]
        try:
            if files and not image_keys:
                content_types = []
                for upload in files:
                    content_type = getattr(upload, "content_type", "")
                    if content_type not in allowed_content_types:
                        raise HTTPException(
                            status_code=400,
                            detail="Only JPEG/PNG/HEIC/HEIF images are supported",
                        )
                    content_types.append(content_type)

                upload_res = _post_json_with_headers(
                    f"{settings.clean_api_base_url}/uploads/presigned-urls",
                    {"count": len(files), "contentTypes": content_types},
                    headers,
                )
                upload_urls = upload_res.get("urls") or []
                if len(upload_urls) != len(files):
                    raise HTTPException(
                        status_code=502,
                        detail="Upload URL count mismatch",
                    )

                image_keys_new: list[str] = []
                for upload_file, upload_info in zip(files, upload_urls):
                    url = upload_info.get("url")
                    key = upload_info.get("key")
                    if not url or not key:
                        raise HTTPException(
                            status_code=502,
                            detail="Upload URL missing",
                        )
                    content_bytes = await upload_file.read()
                    content_type = getattr(upload_file, "content_type", "")
                    try:
                        put_res = requests.put(
                            url,
                            data=content_bytes,
                            headers={"Content-Type": content_type},
                            timeout=10,
                        )
                        put_res.raise_for_status()
                    finally:
                        await upload_file.close()
                    image_keys_new.append(key)

                payload["imageKeys"] = image_keys_new

            _post_json_with_headers(
                f"{settings.clean_api_base_url}/posts", payload, headers)
            success = "Post created"
        except HTTPException as exc:
            error = exc.detail
        except requests.RequestException as exc:
            error = str(exc)

    try:
        # Fetch posts again to update view
        headers_fetch = {}
        data = _fetch_json_with_headers(
            f"{settings.clean_api_base_url}/posts", {"limit": 20}, headers_fetch)
        posts = data.get("items", [])
    except HTTPException as exc:
        if not error:
            error = exc.detail

    return templates.TemplateResponse(
        "home.html",
        _template_context(
            request,
            settings,
            posts=posts,
            error=error,
            success=success,
        ),
    )


@router.get("/posts/{post_id}", name="post_detail")
def post_detail(post_id: str, request: Request, settings: Settings = Depends(get_settings)):
    # Note: Fetching all posts to find one is inefficient but preserving existing logic.
    # The original implementation fetched /posts?limit=50 and filtered in python.
    # Ideally should be /posts/{post_id} if API supports it. Assuming consistent behavior for now.

    headers = {}
    data = _fetch_json_with_headers(
        f"{settings.clean_api_base_url}/posts", {"limit": 50}, headers)
    items = data.get("items", [])

    for item in items:
        if item.get("postId") == post_id:
            return templates.TemplateResponse(
                "post.html",
                _template_context(request, settings, post=item),
            )
    raise HTTPException(status_code=404, detail="Post not found")


@router.delete("/posts/{post_id}", name="post_delete")
def post_delete(post_id: str, request: Request, settings: Settings = Depends(get_settings)):
    """投稿を削除"""
    error = None
    try:
        headers = _auth_header(request, settings)
        if not headers:
            raise HTTPException(
                status_code=401, detail="Authentication required")

        delete_res = requests.delete(
            f"{settings.clean_api_base_url}/posts/{post_id}",
            headers=headers,
            timeout=10,
        )

        if not delete_res.ok:
            detail = delete_res.json().get("detail", "Delete failed") if delete_res.headers.get(
                "content-type", "").startswith("application/json") else delete_res.text
            raise HTTPException(
                status_code=delete_res.status_code,
                detail=detail,
            )

        return delete_res.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/profile", name="profile")
def profile(request: Request, settings: Settings = Depends(get_settings)):
    error = None
    profile_data = None
    try:
        headers = _auth_header(request, settings)
        if headers:
            profile_data = _fetch_json_with_headers(
                f"{settings.clean_api_base_url}/profile", None, headers
            )
    except HTTPException as exc:
        error = exc.detail
    return templates.TemplateResponse(
        "profile.html",
        _template_context(
            request,
            settings,
            api_base_url=settings.clean_api_base_url,
            login_url=_get_auth_urls(settings)[0],
            profile=profile_data,
            error=error,
        ),
    )


@router.post("/profile", name="profile_update")
async def profile_update(request: Request, settings: Settings = Depends(get_settings)):
    error = None
    success = None
    profile_data = None
    form = await request.form()
    nickname = str(form.get("nickname") or "").strip()
    error_detail = None

    headers = _auth_header(request, settings)
    if not headers and not settings.auth_disabled:
        error = "Authentication required"
    elif not nickname:
        error = "Nickname is required"
    else:
        try:
            _post_json_with_headers(
                f"{settings.clean_api_base_url}/profile",
                {"nickname": nickname},
                headers,
            )
            success = "Profile updated"
            profile_data = _fetch_json_with_headers(
                f"{settings.clean_api_base_url}/profile", None, headers
            )
        except HTTPException as exc:
            error = "Failed to update profile"
            error_detail = exc.detail

    return templates.TemplateResponse(
        "profile.html",
        _template_context(
            request,
            settings,
            api_base_url=settings.clean_api_base_url,
            login_url=_get_auth_urls(settings)[0],
            profile=profile_data,
            error=error,
            success=success,
            error_detail=error_detail,
        ),
    )


@router.post("/uploads", name="uploads")
async def uploads(request: Request, settings: Settings = Depends(get_settings)):
    headers = _auth_header(request, settings)
    if not headers and not settings.auth_disabled:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = await request.json()
    count = payload.get("count")
    content_types = payload.get("contentTypes")
    data = _post_json_with_headers(
        f"{settings.clean_api_base_url}/uploads/presigned-urls",
        {"count": count, "contentTypes": content_types},
        headers,
    )
    return data


@router.api_route("/storage/{path:path}", methods=["GET", "PUT", "HEAD"])
async def storage_proxy(path: str, request: Request):
    """MinIO リバースプロキシ（ローカル開発用：ブラウザからのストレージアクセスを中継）"""
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    try:
        resp = requests.request(
            method=request.method,
            url=f"http://minio:9000/{path}",
            params=dict(request.query_params),
            headers=headers,
            data=body,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    resp_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in ("transfer-encoding", "connection", "content-encoding")
    }
    return _Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)
