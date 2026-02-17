import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.request import urlopen

from fastapi import Depends, HTTPException, Request
from jose import jwt

from app.config import settings

JWKS_CACHE_TTL = 3600
_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: dict[str, float] = {}


@dataclass
class UserInfo:
    user_id: str
    is_admin: bool
    nickname: str | None = None


def _oidc_config() -> tuple[str, str, str | None, str]:
    provider = (settings.auth_provider or "aws").lower()
    if provider == "aws":
        if not settings.cognito_user_pool_id or not settings.aws_region:
            raise HTTPException(
                status_code=500, detail="Cognito configuration missing")
        issuer = (
            f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
            f"{settings.cognito_user_pool_id}"
        )
        jwks_url = f"{issuer}/.well-known/jwks.json"
        audience = settings.cognito_client_id
        return provider, jwks_url, audience, issuer

    if provider == "azure":
        if not settings.azure_tenant_id or not settings.azure_client_id:
            raise HTTPException(
                status_code=500, detail="Azure AD configuration missing")
        issuer = settings.auth_issuer or (
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0"
        )
        jwks_url = settings.auth_jwks_url or (
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
        )
        audience = settings.auth_audience or settings.azure_client_id
        return provider, jwks_url, audience, issuer

    if provider == "firebase":
        project_id = settings.gcp_project_id
        if not project_id:
            raise HTTPException(
                status_code=500, detail="GCP Project ID missing for Firebase Auth")

        issuer = f"https://securetoken.google.com/{project_id}"
        jwks_url = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
        audience = project_id
        return provider, jwks_url, audience, issuer

    if provider == "gcp":
        audience = settings.auth_audience or settings.gcp_client_id
        issuer = settings.auth_issuer or "https://accounts.google.com"
        jwks_url = settings.auth_jwks_url or "https://www.googleapis.com/oauth2/v3/certs"
        if not audience:
            raise HTTPException(
                status_code=500, detail="GCP auth configuration missing")
        return provider, jwks_url, audience, issuer

    if settings.auth_issuer and settings.auth_jwks_url:
        return provider, settings.auth_jwks_url, settings.auth_audience, settings.auth_issuer

    raise HTTPException(
        status_code=500, detail="Auth provider configuration missing")


def _get_jwks(jwks_url: str) -> dict[str, Any]:
    now = time.time()
    cached = _jwks_cache.get(jwks_url)
    cached_time = _jwks_cache_time.get(jwks_url, 0.0)
    if cached and (now - cached_time) < JWKS_CACHE_TTL:
        return cached
    with urlopen(jwks_url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    _jwks_cache[jwks_url] = data
    _jwks_cache_time[jwks_url] = now
    return data


def _get_signing_key(token: str, jwks_url: str) -> dict[str, Any]:
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    jwks = _get_jwks(jwks_url).get("keys", [])
    for key in jwks:
        if key.get("kid") == kid:
            return key
    print(f"Signing key not found for kid: {kid}")
    raise HTTPException(status_code=401, detail="Invalid token")


def verify_token(token: str) -> dict[str, Any]:
    provider, jwks_url, audience, issuer = _oidc_config()
    key = _get_signing_key(token, jwks_url)
    try:
        if provider == "aws":
            unverified_claims = jwt.get_unverified_claims(token)
            token_use = unverified_claims.get("token_use")
            if token_use == "access":
                claims = jwt.decode(
                    token,
                    key,
                    algorithms=["RS256"],
                    issuer=issuer,
                    options={"verify_aud": False},
                )
                client_id = claims.get("client_id")
                if client_id != audience:
                    raise HTTPException(
                        status_code=401, detail="Invalid token")
                return claims
        options = {} if audience else {"verify_aud": False}
        options.update({"verify_at_hash": False})
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options=options,
        )
    except Exception as e:
        print(f"Token validation failed: {e}")
        try:
            print(f"Unverified headers: {jwt.get_unverified_header(token)}")
            print(f"Unverified claims: {jwt.get_unverified_claims(token)}")
            print(f"Config: audience={audience}, issuer={issuer}")
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request) -> UserInfo:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header.split(" ", 1)[1]
    claims = verify_token(token)
    user_id = claims.get("sub") or claims.get("oid") or claims.get("uid")
    if not user_id:
        print(f"User ID missing in claims: {claims.keys()}")
        raise HTTPException(status_code=401, detail="Invalid token")

    groups = claims.get("cognito:groups") or claims.get(
        "groups") or claims.get("roles")
    is_admin = False
    if isinstance(groups, str):
        is_admin = groups == settings.admin_group
    elif isinstance(groups, list):
        is_admin = settings.admin_group in groups

    nickname = None
    for key in ["nickname", "name", "preferred_username"]:
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            nickname = value
            break

    return UserInfo(user_id=user_id, is_admin=is_admin, nickname=nickname)


def require_user(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user
