from fastapi import APIRouter, Depends

from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.models import UploadUrlsRequest

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("")
def create_upload_urls(body: UploadUrlsRequest, user: UserInfo = Depends(require_user)) -> dict:
    backend = get_backend()
    return backend.create_upload_urls(body, user)
