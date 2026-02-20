from fastapi import APIRouter, Depends

from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.models import UploadUrlsRequest, UploadUrlsResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presigned-urls", response_model=UploadUrlsResponse)
def generate_upload_urls(
    body: UploadUrlsRequest,
    user: UserInfo = Depends(require_user),
) -> UploadUrlsResponse:
    """画像アップロード用の署名付きURLを生成"""
    backend = get_backend()
    urls = backend.generate_upload_urls(body.count, user, body.content_types)
    return UploadUrlsResponse(urls=urls)
