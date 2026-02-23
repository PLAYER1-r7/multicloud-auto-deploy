from fastapi import APIRouter, Depends, HTTPException
from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.config import settings
from app.models import UploadUrlsRequest, UploadUrlsResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presigned-urls", response_model=UploadUrlsResponse)
def generate_upload_urls(
    body: UploadUrlsRequest,
    user: UserInfo = Depends(require_user),
) -> UploadUrlsResponse:
    """画像アップロード用の署名付きURLを生成"""
    limit = settings.max_images_per_post
    if body.count > limit:
        raise HTTPException(
            status_code=400,
            detail=f"画像は1投稿あたり{limit}枚までです（リクエスト: {body.count}枚）",
        )
    backend = get_backend()
    urls = backend.generate_upload_urls(body.count, user, body.content_types)
    return UploadUrlsResponse(urls=urls)
