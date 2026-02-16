from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class CloudProvider(str, Enum):
    """クラウドプロバイダーの列挙型"""
    LOCAL = "local"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class Post(BaseModel):
    """投稿モデル"""
    id: str = Field(..., alias="postId")
    user_id: str = Field(..., alias="userId")
    nickname: Optional[str] = None
    content: str
    is_markdown: bool = Field(False, alias="isMarkdown")
    image_urls: Optional[list[str]] = Field(None, alias="imageUrls")
    tags: Optional[list[str]] = None
    created_at: str = Field(..., alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class CreatePostBody(BaseModel):
    """投稿作成リクエスト"""
    content: str = Field(..., min_length=1, max_length=10000)
    is_markdown: bool = Field(False, alias="isMarkdown")
    image_keys: Optional[list[str]] = Field(None, alias="imageKeys", max_length=10)
    tags: Optional[list[str]] = Field(None, max_length=10)

    model_config = {"populate_by_name": True}


class ListPostsResponse(BaseModel):
    """投稿一覧レスポンス"""
    items: list[Post]
    limit: int
    next_token: Optional[str] = Field(None, alias="nextToken")

    model_config = {"populate_by_name": True}


class ProfileResponse(BaseModel):
    """プロフィールレスポンス"""
    user_id: str = Field(..., alias="userId")
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class ProfileUpdateRequest(BaseModel):
    """プロフィール更新リクエスト"""
    nickname: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_key: Optional[str] = Field(None, alias="avatarKey")

    model_config = {"populate_by_name": True}


class UploadUrlsRequest(BaseModel):
    """アップロードURL生成リクエスト"""
    count: int = Field(..., ge=1, le=10)


class UploadUrlsResponse(BaseModel):
    """アップロードURLレスポンス"""
    urls: list[dict[str, str]]  # [{"uploadUrl": "...", "key": "..."}]


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    provider: str
    version: str = "3.0.0"
