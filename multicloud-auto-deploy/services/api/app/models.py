from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, model_serializer


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

    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """後方互換性: snake_case と camelCase 両方のフィールド名を返す"""
        return {
            # camelCase (ashnova.v3 形式)
            "postId": self.id,
            "userId": self.user_id,
            "nickname": self.nickname,
            "content": self.content,
            "isMarkdown": self.is_markdown,
            "imageUrls": self.image_urls,
            "tags": self.tags,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            # snake_case (frontend_react 形式)
            "id": self.id,
            "author": self.user_id,  # userId を author としても返す
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "image_url": self.image_urls[0] if self.image_urls else None,
        }


class CreatePostBody(BaseModel):
    """投稿作成リクエスト"""

    content: str = Field(..., min_length=1, max_length=10000)
    is_markdown: bool = Field(False, alias="isMarkdown")
    image_keys: Optional[list[str]] = Field(None, alias="imageKeys", max_length=10)
    tags: Optional[list[str]] = Field(None, max_length=10)

    model_config = {"populate_by_name": True}


class UpdatePostBody(BaseModel):
    """投稿更新リクエスト"""

    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    is_markdown: Optional[bool] = Field(None, alias="isMarkdown")
    image_keys: Optional[list[str]] = Field(None, alias="imageKeys", max_length=10)
    tags: Optional[list[str]] = Field(None, max_length=10)

    model_config = {"populate_by_name": True}


class ListPostsResponse(BaseModel):
    """投稿一覧レスポンス"""

    items: list[Post]
    limit: int
    next_token: Optional[str] = Field(None, alias="nextToken")

    model_config = {"populate_by_name": True}

    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """後方互換性: results と messages フィールドを追加"""
        return {
            "items": self.items,
            "results": self.items,  # ashnova.v1 互換
            "messages": self.items,  # frontend_react 互換
            "limit": self.limit,
            "nextToken": self.next_token,
            "total": len(self.items),  # frontend_react 互換
            "page": 1,  # frontend_react 互換
            "page_size": self.limit,  # frontend_react 互換
        }


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
