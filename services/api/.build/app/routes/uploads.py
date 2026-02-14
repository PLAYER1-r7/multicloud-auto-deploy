"""画像アップロードAPI ルーター"""
import uuid
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    """アップロードレスポンス"""

    url: str
    filename: str
    size: int
    content_type: str


def get_minio_client() -> Minio:
    """MinIOクライアントを取得"""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="画像をアップロード",
    description="画像ファイルをアップロードしてURLを取得",
)
async def upload_image(
    file: Annotated[UploadFile, File(description="アップロードする画像ファイル")],
    minio_client: Annotated[Minio, Depends(get_minio_client)],
):
    """画像をアップロード"""

    # Content-Typeチェック
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {file.content_type}. "
            f"Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # ファイル拡張子チェック
    if file.filename:
        extension = "." + file.filename.split(".")[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension: {extension}. "
                f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    # ファイルを読み込み
    content = await file.read()
    file_size = len(content)

    # ファイルサイズチェック
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {file_size} bytes. "
            f"Maximum allowed: {settings.max_upload_size} bytes",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    # ユニークなファイル名を生成
    file_ext = "." + file.filename.split(".")[-1].lower() if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    object_key = f"images/{unique_filename}"

    # MinIOにアップロード
    try:
        minio_client.put_object(
            bucket_name=settings.minio_bucket_name,
            object_name=object_key,
            data=BytesIO(content),
            length=file_size,
            content_type=file.content_type,
        )
    except S3Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}",
        )

    # 画像URLを生成（ブラウザからアクセス可能なURL）
    # NOTE: 本番環境ではCloudFrontやCDNのURLを使用
    # ローカル: minio → localhost に変換（Dockerコンテナ外からアクセスできるように）
    minio_public_endpoint = settings.minio_endpoint.replace("minio:", "localhost:")
    image_url = f"http://{minio_public_endpoint}/{settings.minio_bucket_name}/{object_key}"

    return UploadResponse(
        url=image_url,
        filename=unique_filename,
        size=file_size,
        content_type=file.content_type or "application/octet-stream",
    )
