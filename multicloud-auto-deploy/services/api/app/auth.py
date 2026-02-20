import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


@dataclass
class UserInfo:
    """ユーザー情報"""

    user_id: str
    email: Optional[str] = None
    groups: Optional[list[str]] = None

    @property
    def is_admin(self) -> bool:
        """管理者かどうか"""
        return self.groups is not None and "Admins" in self.groups


def get_jwt_verifier():
    """JWT verifierインスタンスを取得（設定に基づいて）"""
    from app.config import settings
    from app.jwt_verifier import JWTVerifier

    if not settings.auth_provider:
        return None

    # Build config based on provider
    if settings.auth_provider == "cognito":
        config = {
            "region": settings.aws_region,
            "user_pool_id": settings.cognito_user_pool_id,
            "client_id": settings.cognito_client_id,
        }
    elif settings.auth_provider == "firebase":
        config = {
            "project_id": settings.gcp_project_id,
        }
    elif settings.auth_provider == "azure":
        config = {
            "tenant_id": settings.azure_tenant_id,
            "client_id": settings.azure_client_id,
            "is_b2c": True,  # Assuming B2C for now
            "tenant_name": (
                settings.azure_tenant_id.split(".")[0]
                if settings.azure_tenant_id
                else None
            ),
        }
    else:
        logger.warning(f"Unknown auth provider: {settings.auth_provider}")
        return None

    return JWTVerifier(settings.auth_provider, config)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserInfo]:
    """現在のユーザーを取得（JWTトークンから）"""
    from app.config import settings

    # 認証が無効の場合はテストユーザーを返す
    if settings.auth_disabled:
        return UserInfo(
            user_id="test-user-1", email="test@example.com", groups=["Admins"]
        )

    # トークンがない場合
    if not credentials:
        return None

    # JWT検証
    verifier = get_jwt_verifier()
    if not verifier:
        logger.error("JWT verifier not configured")
        return None

    try:
        # トークンを検証
        claims = verifier.verify_token(credentials.credentials)
        if not claims:
            logger.warning("Token verification failed")
            return None

        # ユーザー情報を抽出
        user_info_dict = verifier.extract_user_info(claims)
        return UserInfo(
            user_id=user_info_dict["user_id"],
            email=user_info_dict.get("email"),
            groups=user_info_dict.get("groups", []),
        )
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


async def require_user(
    user: Optional[UserInfo] = Depends(get_current_user),
) -> UserInfo:
    """認証が必要なエンドポイント用の依存関数"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(user: UserInfo = Depends(require_user)) -> UserInfo:
    """管理者権限が必要なエンドポイント用の依存関数"""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )

    return user
