import base64
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from azure.cosmos import CosmosClient
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas
from fastapi import HTTPException

from app.config import settings
from app.auth import UserInfo
from app.models import CreatePostBody, Post, ProfileResponse, ProfileUpdateRequest, UploadUrlsRequest

logger = logging.getLogger(__name__)

_cosmos_client: CosmosClient | None = None
_container_client = None
_blob_service: BlobServiceClient | None = None


def _get_container():
    global _cosmos_client, _container_client
    if _container_client is not None:
        return _container_client
    if not settings.cosmos_db_endpoint or not settings.cosmos_db_key:
        raise HTTPException(
            status_code=500, detail="Cosmos DB configuration missing")
    _cosmos_client = CosmosClient(
        settings.cosmos_db_endpoint, credential=settings.cosmos_db_key)
    database = _cosmos_client.get_database_client(settings.cosmos_db_database)
    _container_client = database.get_container_client(
        settings.cosmos_db_container)
    return _container_client


def _get_blob_service() -> BlobServiceClient:
    global _blob_service
    if _blob_service is not None:
        return _blob_service
    if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
        raise HTTPException(
            status_code=500, detail="Azure Storage configuration missing")
    account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
    _blob_service = BlobServiceClient(
        account_url=account_url, credential=settings.azure_storage_account_key)
    return _blob_service


def _encode_token(token: str | None) -> str | None:
    if not token:
        return None
    return base64.b64encode(token.encode("utf-8")).decode("utf-8")


def _decode_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return base64.b64decode(token.encode("utf-8")).decode("utf-8")
    except Exception:
        logger.warning("Invalid nextToken provided")
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _blob_url(key: str, permission: BlobSasPermissions, expiry_seconds: int) -> str:
    if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
        raise HTTPException(
            status_code=500, detail="Azure Storage configuration missing")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)
    sas = generate_blob_sas(
        account_name=settings.azure_storage_account_name,
        container_name=settings.azure_storage_container,
        blob_name=key,
        account_key=settings.azure_storage_account_key,
        permission=permission,
        expiry=expires_at,
    )
    return (
        f"https://{settings.azure_storage_account_name}.blob.core.windows.net/"
        f"{settings.azure_storage_container}/{key}?{sas}"
    )


def _build_image_urls(keys: list[str]) -> list[str] | None:
    if not keys:
        return None
    # Public URL for caching and cost reduction
    if not settings.azure_storage_account_name or not settings.azure_storage_container:
        return None

    return [
        f"https://{settings.azure_storage_account_name}.blob.core.windows.net/"
        f"{settings.azure_storage_container}/{key}"
        for key in keys
    ]


class AzureBackend:
    def list_posts(self, limit: int, next_token: str | None, tag: str | None) -> tuple[list[Post], str | None]:
        container = _get_container()
        query = "SELECT * FROM c WHERE c.pk = @pk ORDER BY c.createdAt DESC"
        params = [{"name": "@pk", "value": "POSTS"}]
        continuation = _decode_token(next_token)
        page_iter = container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
            max_item_count=limit,
        ).by_page(continuation_token=continuation)
        page = next(page_iter, [])
        items = list(page)
        continuation_out = getattr(page_iter, "continuation_token", None)

        posts: list[Post] = []
        for item in items:
            image_keys = item.get("imageKeys") or ([] if item.get(
                "imageKey") is None else [item.get("imageKey")])
            image_keys = [key for key in image_keys if isinstance(key, str)]
            post = Post(
                postId=item.get("postId"),
                userId=item.get("userId"),
                nickname=item.get("nickname"),
                content=item.get("content"),
                createdAt=item.get("createdAt"),
                isMarkdown=item.get("isMarkdown"),
                tags=item.get("tags"),
                imageUrls=_build_image_urls(image_keys),
            )
            posts.append(post)

        if tag:
            posts = [item for item in posts if item.tags and tag in item.tags]

        return posts, _encode_token(continuation_out)

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        container = _get_container()
        post_id = str(uuid.uuid4())
        created_at = _now_iso()

        profile = None
        try:
            profile = container.read_item(
                item=f"USER#{user.user_id}", partition_key=f"USER#{user.user_id}")
        except Exception:
            profile = None

        nickname = None
        if profile:
            nickname = profile.get("nickname")
        if not nickname:
            nickname = user.nickname

        item: dict[str, Any] = {
            "id": post_id,
            "pk": "POSTS",
            "postId": post_id,
            "userId": user.user_id,
            "content": body.content,
            "createdAt": created_at,
            "docType": "post",
        }
        if body.imageKeys:
            item["imageKeys"] = body.imageKeys
        if body.isMarkdown:
            item["isMarkdown"] = True
        if body.tags:
            item["tags"] = body.tags
        if nickname:
            item["nickname"] = nickname

        container.upsert_item(item)
        return {"item": item}

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        container = _get_container()
        try:
            post = container.read_item(item=post_id, partition_key="POSTS")
        except Exception:
            raise HTTPException(status_code=404, detail="Post not found")

        if not user.is_admin and post.get("userId") != user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        image_keys = post.get("imageKeys") or ([] if post.get(
            "imageKey") is None else [post.get("imageKey")])
        image_keys = [key for key in image_keys if isinstance(key, str)]

        if image_keys:
            service = _get_blob_service()
            container = service.get_container_client(
                config.AZURE_STORAGE_CONTAINER)
            for key in image_keys:
                try:
                    container.delete_blob(key)
                except Exception:
                    logger.exception("Failed to delete image",
                                     extra={"key": key})

        try:
            container.delete_item(item=post_id, partition_key="POSTS")
        except Exception:
            logger.exception("Failed to delete post")
            raise HTTPException(status_code=500, detail="Delete failed")

        return {"message": "Post deleted", "postId": post_id}

    def get_profile(self, user: UserInfo) -> ProfileResponse:
        container = _get_container()
        try:
            item = container.read_item(
                item=f"USER#{user.user_id}", partition_key=f"USER#{user.user_id}")
        except Exception:
            item = None
        if not item:
            return ProfileResponse(userId=user.user_id, nickname="")

        return ProfileResponse(
            userId=user.user_id,
            nickname=item.get("nickname") or "",
            updatedAt=item.get("updatedAt"),
            createdAt=item.get("createdAt"),
        )

    def update_profile(self, body: ProfileUpdateRequest, user: UserInfo) -> ProfileResponse:
        container = _get_container()
        now = _now_iso()
        created_at = now
        try:
            existing = container.read_item(
                item=f"USER#{user.user_id}", partition_key=f"USER#{user.user_id}")
            created_at = existing.get("createdAt") or created_at
        except Exception:
            pass

        item = {
            "id": f"USER#{user.user_id}",
            "pk": f"USER#{user.user_id}",
            "userId": user.user_id,
            "nickname": body.nickname,
            "updatedAt": now,
            "createdAt": created_at,
            "docType": "profile",
        }
        container.upsert_item(item)

        return ProfileResponse(
            userId=user.user_id,
            nickname=body.nickname,
            updatedAt=now,
            createdAt=created_at,
        )

    def create_upload_urls(self, body: UploadUrlsRequest, user: UserInfo) -> dict:
        if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
            raise HTTPException(
                status_code=500, detail="Azure Storage configuration missing")

        post_id = str(uuid.uuid4())
        content_types = body.contentTypes or ["image/jpeg"] * body.count
        extension_map = {
            "image/jpeg": "jpeg",
            "image/png": "png",
            "image/heic": "heic",
            "image/heif": "heif",
        }
        urls = []
        for index in range(body.count):
            content_type = content_types[index]
            extension = extension_map.get(content_type, "jpeg")
            key = f"images/{post_id}-{index}-{secrets.token_hex(8)}.{extension}"
            url = _blob_url(
                key,
                BlobSasPermissions(create=True, write=True),
                settings.presigned_url_expiry,
            )
            urls.append({"url": url, "key": key, "contentType": content_type})

        return {
            "postId": post_id,
            "urls": urls,
            "expiresIn": settings.presigned_url_expiry,
        }
