from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.models import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: str) -> ProfileResponse:
    """プロフィールを取得"""
    backend = get_backend()
    return backend.get_profile(user_id)


@router.get("", response_model=ProfileResponse)
def get_my_profile(user: UserInfo = Depends(require_user)) -> ProfileResponse:
    """自分のプロフィールを取得"""
    backend = get_backend()
    return backend.get_profile(user.user_id)


@router.put("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdateRequest,
    user: UserInfo = Depends(require_user),
) -> ProfileResponse:
    """プロフィールを更新"""
    backend = get_backend()
    return backend.update_profile(user, body)
