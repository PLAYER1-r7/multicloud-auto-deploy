from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/limits", tags=["limits"])


@router.get("")
def get_limits() -> dict:
    """サービス制限値を返す (認証不要、フロントエンドが起動時に取得して利用)"""
    return {
        "maxImagesPerPost": settings.max_images_per_post,
    }
