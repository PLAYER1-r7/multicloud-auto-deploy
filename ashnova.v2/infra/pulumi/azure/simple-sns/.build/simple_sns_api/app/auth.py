import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.request import urlopen

from fastapi import Depends, HTTPException, Request
from jose import jwt

from app import config

JWKS_CACHE_TTL = 3600
_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: dict[str, float] = {}


@dataclass
class UserInfo:
    user_id: str
    is_admin: bool
    nickname: str | None = None


def _oidc_config() -> tuple[str, str, str | None, str]:
    provider = (config.AUTH_PROVIDER or "aws").lower()
    if provider == "aws":
        if not config.COGNITO_USER_POOL_ID or not config.AWS_REGION:
            raise HTTPException(
                status_code=500, detail="Cognito configuration missing")
        issuer = (
            f"https://cognito-idp.{config.AWS_REGION}.amazonaws.com/"
            f"{config.COGNITO_USER_POOL_ID}"
        )
        jwks_url = f"{issuer}/.well-known/jwks.json"
        audience = config.COGNITO_CLIENT_ID
        return provider, jwks_url, audience, issuer

    if provider == "azure":
        if not config.AZURE_TENANT_ID or not config.AZURE_CLIENT_ID:
            raise HTTPException(
                status_code=500, detail="Azure AD configuration missing")
        issuer = config.AUTH_ISSUER or (
            f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/v2.0"
        )
        jwks_url = config.AUTH_JWKS_URL or (
            f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/discovery/v2.0/keys"
        )
        audience = config.AUTH_AUDIENCE or config.AZURE_CLIENT_ID
        return provider, jwks_url, audience, issuer

    if provider == "gcp":
        audience = config.AUTH_AUDIENCE or config.GCP_CLIENT_ID
        issuer = config.AUTH_ISSUER or "https://accounts.google.com"
        jwks_url = config.AUTH_JWKS_URL or "https://www.googleapis.com/oauth2/v3/certs"
        if not audience:
            raise HTTPException(
                status_code=500, detail="GCP auth configuration missing")
        return provider, jwks_url, audience, issuer

    if config.AUTH_ISSUER and config.AUTH_JWKS_URL:
        return provider, config.AUTH_JWKS_URL, config.AUTH_AUDIENCE, config.AUTH_ISSUER

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
    raise HTTPException(status_code=401, detail="Invalid token")


def verify_token(token: str) -> dict[str, Any]:
    provider, jwks_url, audience, issuer = _oidc_config()
    key = _get_signing_key(token, jwks_url)
    unverified_claims = jwt.get_unverified_claims(token)
    try:
        if provider == "aws":
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
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options=options,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request) -> UserInfo:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header.split(" ", 1)[1]
    claims = verify_token(token)
    user_id = claims.get("sub") or claims.get("oid") or claims.get("uid")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    groups = claims.get("cognito:groups") or claims.get(
        "groups") or claims.get("roles")
    is_admin = False
    if isinstance(groups, str):
        is_admin = groups == config.ADMIN_GROUP
    elif isinstance(groups, list):
        is_admin = config.ADMIN_GROUP in groups

    nickname = None
    for key in ["nickname", "name", "preferred_username"]:
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            nickname = value
            break

    return UserInfo(user_id=user_id, is_admin=is_admin, nickname=nickname)


def require_user(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user
