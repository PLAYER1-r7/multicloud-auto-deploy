from fastapi import APIRouter, Depends

from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.models import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile(user: UserInfo = Depends(require_user)) -> ProfileResponse:
    backend = get_backend()
    return backend.get_profile(user)


@router.post("")
def update_profile(
    body: ProfileUpdateRequest, user: UserInfo = Depends(require_user)
) -> ProfileResponse:
    backend = get_backend()
    return backend.update_profile(body, user)
