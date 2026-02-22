"""Azure Backend Implementation using Cosmos DB + Blob Storage"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_exceptions
    _cosmos_available = True
except ImportError:
    _cosmos_available = False
    logger.warning("azure-cosmos not available")

try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    _blob_available = True
except ImportError:
    _blob_available = False
    logger.warning("azure-storage-blob not available")


class AzureBackend(BackendBase):
    """Azure実装 (Cosmos DB + Blob Storage + Azure AD B2C)"""

    def __init__(self):
        if not _cosmos_available:
            raise ImportError("azure-cosmos is required for Azure backend")

        endpoint = settings.cosmos_db_endpoint
        key = settings.cosmos_db_key
        if not endpoint or not key:
            raise ValueError(
                "Cosmos DB credentials not configured. "
                "Set COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables."
            )

        self.client = CosmosClient(endpoint, key)
        db_name = settings.cosmos_db_database or "simple-sns"

        # データベースを取得または作成
        self.database = self.client.create_database_if_not_exists(id=db_name)

        # posts コンテナ
        self.posts_container = self.database.create_container_if_not_exists(
            id="posts",
            partition_key=PartitionKey(path="/postId"),
        )
        # profiles コンテナ
        self.profiles_container = self.database.create_container_if_not_exists(
            id="profiles",
            partition_key=PartitionKey(path="/userId"),
        )

        # Blob Storage の設定
        self.storage_account = settings.azure_storage_account_name
        self.storage_key = settings.azure_storage_account_key
        self.images_container = settings.azure_storage_container

        logger.info(
            f"AzureBackend initialized: db={db_name}, "
            f"storage_account={self.storage_account}"
        )

    def _item_to_post(self, item: dict) -> Post:
        """Cosmos DBアイテムをPostモデルに変換"""
        return Post(
            postId=item.get("postId", item.get("id", "")),
            userId=item.get("userId", "unknown"),
            content=item.get("content", ""),
            isMarkdown=item.get("isMarkdown", False),
            imageUrls=item.get("imageUrls", []),
            tags=item.get("tags", []),
            createdAt=item.get("createdAt", datetime.now(timezone.utc).isoformat()),
            updatedAt=item.get("updatedAt"),
        )

    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """Cosmos DBから投稿一覧を取得"""
        try:
            if tag:
                query = (
                    "SELECT * FROM c WHERE ARRAY_CONTAINS(c.tags, @tag) "
                    "ORDER BY c.createdAt DESC OFFSET 0 LIMIT @limit"
                )
                parameters = [
                    {"name": "@tag", "value": tag},
                    {"name": "@limit", "value": limit + 1},
                ]
            else:
                query = "SELECT * FROM c ORDER BY c.createdAt DESC OFFSET 0 LIMIT @limit"
                parameters = [{"name": "@limit", "value": limit + 1}]

            # next_token (offset) を数値トークンとして扱う
            offset = 0
            if next_token:
                try:
                    offset = int(next_token)
                except (ValueError, TypeError):
                    offset = 0

            if offset > 0:
                if tag:
                    query = (
                        "SELECT * FROM c WHERE ARRAY_CONTAINS(c.tags, @tag) "
                        "ORDER BY c.createdAt DESC OFFSET @offset LIMIT @limit"
                    )
                    parameters = [
                        {"name": "@tag", "value": tag},
                        {"name": "@offset", "value": offset},
                        {"name": "@limit", "value": limit + 1},
                    ]
                else:
                    query = (
                        "SELECT * FROM c ORDER BY c.createdAt DESC "
                        "OFFSET @offset LIMIT @limit"
                    )
                    parameters = [
                        {"name": "@offset", "value": offset},
                        {"name": "@limit", "value": limit + 1},
                    ]

            items = list(self.posts_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            ))

            output_next_token = None
            if len(items) > limit:
                items = items[:limit]
                output_next_token = str(offset + limit)

            posts = [self._item_to_post(item) for item in items]
            return posts, output_next_token

        except Exception as e:
            logger.error(f"Error listing posts from Cosmos DB: {e}")
            raise

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """Cosmos DBに投稿を作成"""
        try:
            post_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).isoformat()

            # 画像キーをURLに変換
            image_urls = []
            if body.image_keys:
                image_urls = [
                    f"https://{self.storage_account}.blob.core.windows.net/"
                    f"{self.images_container}/{key}"
                    for key in body.image_keys
                ]

            item = {
                "id": post_id,
                "postId": post_id,
                "userId": user.user_id,
                "content": body.content,
                "isMarkdown": body.is_markdown,
                "imageUrls": image_urls,
                "tags": body.tags or [],
                "createdAt": now_str,
                "updatedAt": None,
            }

            self.posts_container.create_item(body=item)
            logger.info(f"Created post {post_id} by user {user.user_id}")

            return Post(
                postId=post_id,
                userId=user.user_id,
                content=body.content,
                isMarkdown=body.is_markdown,
                imageUrls=image_urls,
                tags=body.tags or [],
                createdAt=now_str,
            ).model_dump()

        except Exception as e:
            logger.error(f"Error creating post in Cosmos DB: {e}")
            raise

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """Cosmos DBから投稿を削除"""
        try:
            item = self.posts_container.read_item(item=post_id, partition_key=post_id)
        except cosmos_exceptions.CosmosResourceNotFoundError:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Post not found")

        if item.get("userId") != user.user_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized")

        self.posts_container.delete_item(item=post_id, partition_key=post_id)
        logger.info(f"Deleted post {post_id}")
        return {"message": "Post deleted successfully", "postId": post_id}

    def get_profile(self, user_id: str) -> ProfileResponse:
        """Cosmos DBからプロフィールを取得"""
        try:
            item = self.profiles_container.read_item(item=user_id, partition_key=user_id)
            return ProfileResponse(
                userId=user_id,
                nickname=item.get("nickname"),
                bio=item.get("bio"),
                avatarUrl=item.get("avatarUrl"),
                createdAt=item.get("createdAt"),
                updatedAt=item.get("updatedAt"),
            )
        except cosmos_exceptions.CosmosResourceNotFoundError:
            return ProfileResponse(userId=user_id)
        except Exception as e:
            logger.error(f"Error getting profile {user_id}: {e}")
            raise

    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """Cosmos DBのプロフィールを更新"""
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            user_id = user.user_id

            try:
                existing = self.profiles_container.read_item(
                    item=user_id, partition_key=user_id
                )
            except cosmos_exceptions.CosmosResourceNotFoundError:
                existing = {
                    "id": user_id,
                    "userId": user_id,
                    "createdAt": now_str,
                }

            if body.nickname is not None:
                existing["nickname"] = body.nickname
            if body.bio is not None:
                existing["bio"] = body.bio
            if body.avatar_key is not None:
                existing["avatarUrl"] = (
                    f"https://{self.storage_account}.blob.core.windows.net/"
                    f"{self.images_container}/{body.avatar_key}"
                )
            existing["updatedAt"] = now_str

            self.profiles_container.upsert_item(body=existing)
            return self.get_profile(user_id)

        except Exception as e:
            logger.error(f"Error updating profile {user.user_id}: {e}")
            raise

    def generate_upload_urls(
        self,
        count: int,
        user: UserInfo,
        content_types: Optional[list[str]] = None,
    ) -> list[dict[str, str]]:
        """Azure Blob Storage の SAS URLを生成"""
        if not _blob_available:
            raise ImportError("azure-storage-blob is required")

        ext_map = {
            "image/jpeg": "jpg", "image/jpg": "jpg",
            "image/png": "png", "image/gif": "gif",
            "image/webp": "webp", "image/heic": "heic", "image/heif": "heif",
        }
        urls = []
        account = self.storage_account
        key = self.storage_key
        container = self.images_container

        for i in range(count):
            ct = (
                content_types[i]
                if content_types and i < len(content_types)
                else None
            ) or "image/jpeg"
            ext = ext_map.get(ct, "jpg")
            blob_name = f"images/{user.user_id}/{uuid.uuid4()}.{ext}"
            sas_token = generate_blob_sas(
                account_name=account,
                container_name=container,
                blob_name=blob_name,
                account_key=key,
                permission=BlobSasPermissions(write=True, create=True),
                expiry=datetime.now(timezone.utc) + timedelta(seconds=settings.presigned_url_expiry),
                content_type=ct,
            )
            upload_url = (
                f"https://{account}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"
            )
            urls.append({"url": upload_url, "key": blob_name})

        return urls
