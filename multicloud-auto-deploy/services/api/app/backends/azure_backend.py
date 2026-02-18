"""
Azure Backend Implementation
Cosmos DB + Blob Storage + Azure AD
"""
import base64
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, UpdatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo
from app.config import settings

logger = logging.getLogger(__name__)

# Global client instances (lazy initialization)
_cosmos_client = None
_container_client = None
_blob_service = None


def _get_container():
    """Get or create Cosmos DB container client"""
    global _cosmos_client, _container_client
    if _container_client is not None:
        return _container_client
    
    if not settings.cosmos_db_endpoint or not settings.cosmos_db_key:
        raise ValueError("COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables are required")
    
    try:
        from azure.cosmos import CosmosClient
        _cosmos_client = CosmosClient(
            settings.cosmos_db_endpoint,
            credential=settings.cosmos_db_key
        )
        database = _cosmos_client.get_database_client(settings.cosmos_db_database)
        _container_client = database.get_container_client(settings.cosmos_db_container)
        logger.info(f"Cosmos DB container client initialized: {settings.cosmos_db_database}/{settings.cosmos_db_container}")
        return _container_client
    except ImportError:
        raise ImportError("azure-cosmos package is required for Azure backend")


def _get_blob_service():
    """Get or create Blob Service client"""
    global _blob_service
    if _blob_service is not None:
        return _blob_service
    
    if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY environment variables are required")
    
    try:
        from azure.storage.blob import BlobServiceClient
        account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
        _blob_service = BlobServiceClient(
            account_url=account_url,
            credential=settings.azure_storage_account_key
        )
        logger.info(f"Blob Service client initialized: {account_url}")
        return _blob_service
    except ImportError:
        raise ImportError("azure-storage-blob package is required for Azure backend")


def _encode_token(token: Optional[str]) -> Optional[str]:
    """Encode continuation token"""
    if not token:
        return None
    return base64.b64encode(token.encode("utf-8")).decode("utf-8")


def _decode_token(token: Optional[str]) -> Optional[str]:
    """Decode continuation token"""
    if not token:
        return None
    try:
        return base64.b64decode(token.encode("utf-8")).decode("utf-8")
    except Exception:
        logger.warning("Invalid pagination token provided")
        return None


def _now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def _blob_url(key: str, permission, expiry_seconds: int) -> str:
    """Generate Blob Storage SAS URL"""
    if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
        raise ValueError("Azure Storage configuration is required")
    
    try:
        from azure.storage.blob import generate_blob_sas
        
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
    except ImportError:
        raise ImportError("azure-storage-blob package is required")


def _build_image_urls(keys: list[str]) -> Optional[list[str]]:
    """Build public URLs for Blob Storage objects"""
    if not keys:
        return None
    if not settings.azure_storage_account_name or not settings.azure_storage_container:
        return None
    
    return [
        f"https://{settings.azure_storage_account_name}.blob.core.windows.net/"
        f"{settings.azure_storage_container}/{key}"
        for key in keys
    ]


class AzureBackend(BackendBase):
    """Azure実装 (Cosmos DB + Blob Storage + Azure AD)"""
    
    def __init__(self):
        """Initialize Azure backend"""
        logger.info("Initializing Azure backend")
        # Clients are lazily initialized when first used
    
    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """List posts from Cosmos DB"""
        container = _get_container()
        
        # Query posts across all partitions
        query = "SELECT * FROM c WHERE c.docType = @docType ORDER BY c.createdAt DESC"
        params = [{"name": "@docType", "value": "post"}]
        
        # Decode continuation token
        continuation = _decode_token(next_token)
        
        # Execute query with pagination
        page_iter = container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
            max_item_count=limit,
        ).by_page(continuation_token=continuation)
        
        page = next(page_iter, [])
        items = list(page)
        continuation_out = getattr(page_iter, "continuation_token", None)
        
        logger.info(f"Found {len(items)} posts in Cosmos DB")
        
        posts: list[Post] = []
        for item in items:
            # Handle image keys (may be list or single value)
            image_keys = item.get("imageKeys") or ([] if item.get("imageKey") is None else [item.get("imageKey")])
            image_keys = [key for key in image_keys if isinstance(key, str)]
            
            post = Post(
                postId=item.get("postId"),
                userId=item.get("userId"),
                nickname=item.get("nickname"),
                content=item.get("content"),
                createdAt=item.get("createdAt"),
                updatedAt=item.get("updatedAt") or item.get("createdAt"),
                isMarkdown=item.get("isMarkdown"),
                tags=item.get("tags"),
                imageUrls=_build_image_urls(image_keys),
            )
            posts.append(post)
        
        # Client-side tag filtering
        if tag:
            posts = [p for p in posts if p.tags and tag in p.tags]
        
        return posts, _encode_token(continuation_out)
    
    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """Create a new post in Cosmos DB"""
        logger.info(f"Creating post for user {user.user_id}")
        
        container = _get_container()
        post_id = str(uuid.uuid4())
        created_at = _now_iso()
        
        # Get user's nickname from profile
        profile = None
        try:
            profile = container.read_item(
                item=f"USER_{user.user_id}",
                partition_key=user.user_id
            )
        except Exception:
            profile = None
        
        nickname = None
        if profile:
            nickname = profile.get("nickname")
        if not nickname:
            # Use email or user_id as fallback since UserInfo doesn't have nickname attribute
            nickname = user.email if user.email else user.user_id
        
        # Build post document
        item: dict[str, Any] = {
            "id": post_id,
            "userId": user.user_id,
            "postId": post_id,
            "content": body.content,
            "createdAt": created_at,
            "updatedAt": created_at,
            "docType": "post",
        }
        
        if body.image_keys:
            item["imageKeys"] = body.image_keys
        if body.is_markdown:
            item["isMarkdown"] = True
        if body.tags:
            item["tags"] = body.tags
        if nickname:
            item["nickname"] = nickname
        
        logger.info(f"Writing post {post_id} to Cosmos DB with userId={user.user_id}")
        try:
            container.upsert_item(item)
            logger.info(f"Successfully wrote post {post_id}")
        except Exception as e:
            logger.error(f"Failed to write post {post_id}: {type(e).__name__}: {e}")
            raise
        
        return {"item": item}
    
    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """Delete a post from Cosmos DB"""
        container = _get_container()
        
        # First query to find the post and get its userId
        try:
            query = "SELECT * FROM c WHERE c.id = @id AND c.docType = @docType"
            params = [{"name": "@id", "value": post_id}, {"name": "@docType", "value": "post"}]
            items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
            if not items:
                raise ValueError(f"Post not found: {post_id}")
            post = items[0]
        except Exception as e:
            if "Post not found" in str(e):
                raise
            raise ValueError(f"Post not found: {post_id}")
        
        # Check permissions
        if not user.is_admin and post.get("userId") != user.user_id:
            raise PermissionError("You do not have permission to delete this post")
        
        # Delete associated images from Blob Storage
        image_keys = post.get("imageKeys") or ([] if post.get("imageKey") is None else [post.get("imageKey")])
        image_keys = [key for key in image_keys if isinstance(key, str)]
        
        if image_keys:
            service = _get_blob_service()
            container_client = service.get_container_client(settings.azure_storage_container)
            for key in image_keys:
                try:
                    container_client.delete_blob(key)
                    logger.info(f"Deleted blob: {key}")
                except Exception as e:
                    logger.error(f"Failed to delete blob {key}: {e}")
        
        # Delete post document
        try:
            container.delete_item(item=post_id, partition_key=post.get("userId"))
            logger.info(f"Deleted post {post_id}")
        except Exception as e:
            logger.error(f"Failed to delete post: {e}")
            raise
        
        return {
            "status": "deleted",
            "post_id": post_id,
        }
    
    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        """Update a post in Cosmos DB"""
        container = _get_container()
        
        # First query to find the post and get its userId
        try:
            query = "SELECT * FROM c WHERE c.id = @id AND c.docType = @docType"
            params = [{"name": "@id", "value": post_id}, {"name": "@docType", "value": "post"}]
            items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
            if not items:
                raise ValueError(f"Post not found: {post_id}")
            post = items[0]
        except Exception as e:
            if "Post not found" in str(e):
                raise
            raise ValueError(f"Post not found: {post_id}")
        
        # Check permissions
        if not user.is_admin and post.get("userId") != user.user_id:
            raise PermissionError("You do not have permission to update this post")
        
        # Update fields
        now = _now_iso()
        post["updatedAt"] = now
        
        if body.content is not None:
            post["content"] = body.content
        if body.tags is not None:
            post["tags"] = body.tags
        if body.image_keys is not None:
            post["imageKeys"] = body.image_keys
        
        # Replace document
        container.replace_item(item=post_id, body=post)
        logger.info(f"Updated post {post_id}")
        
        return {
            "status": "updated",
            "post_id": post_id,
            "updated_at": now,
        }
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        """Get user profile from Cosmos DB"""
        container = _get_container()
        
        try:
            item = container.read_item(
                item=f"USER_{user_id}",
                partition_key=user_id
            )
        except Exception:
            item = None
        
        if not item:
            return ProfileResponse(userId=user_id, nickname="")
        
        return ProfileResponse(
            userId=user_id,
            nickname=item.get("nickname") or "",
            updatedAt=item.get("updatedAt"),
            createdAt=item.get("createdAt"),
        )
    
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """Update user profile in Cosmos DB"""
        container = _get_container()
        now = _now_iso()
        
        # Preserve createdAt if exists
        created_at = now
        try:
            existing = container.read_item(
                item=f"USER_{user.user_id}",
                partition_key=user.user_id
            )
            created_at = existing.get("createdAt") or created_at
        except Exception:
            pass
        
        item = {
            "id": f"USER_{user.user_id}",
            "userId": user.user_id,
            "nickname": body.nickname,
            "updatedAt": now,
            "createdAt": created_at,
            "docType": "profile",
        }
        container.upsert_item(item)
        logger.info(f"Updated profile for user {user.user_id}")
        
        return ProfileResponse(
            userId=user.user_id,
            nickname=body.nickname,
            updatedAt=now,
            createdAt=created_at,
        )
    
    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        """Generate SAS URLs for Blob Storage uploads"""
        if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
            raise ValueError("Azure Storage configuration is required")
        
        try:
            from azure.storage.blob import BlobSasPermissions
        except ImportError:
            raise ImportError("azure-storage-blob package is required")
        
        post_id = str(uuid.uuid4())
        content_type = "image/jpeg"  # Default content type
        
        urls = []
        for index in range(count):
            key = f"images/{post_id}-{index}-{secrets.token_hex(8)}.jpeg"
            url = _blob_url(
                key,
                BlobSasPermissions(create=True, write=True),
                settings.presigned_url_expiry,
            )
            urls.append({
                "url": url,
                "key": key,
                "fields": {},
            })
            logger.info(f"Generated SAS URL for key: {key}")
        
        return urls
