"""
GCP Backend Implementation
Firestore + Cloud Storage + Firebase Auth
"""
import base64
import json
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
_firestore_client = None
_storage_client = None


def _get_firestore():
    """Get or create Firestore client"""
    global _firestore_client
    if _firestore_client:
        return _firestore_client
    
    if not settings.gcp_project_id:
        raise ValueError("GCP_PROJECT_ID environment variable is required")
    
    try:
        from google.cloud import firestore
        _firestore_client = firestore.Client(project=settings.gcp_project_id)
        logger.info(f"Firestore client initialized for project: {settings.gcp_project_id}")
        return _firestore_client
    except ImportError:
        raise ImportError("google-cloud-firestore package is required for GCP backend")


def _get_storage():
    """Get or create Cloud Storage client"""
    global _storage_client
    if _storage_client:
        return _storage_client
    
    if not settings.gcp_project_id:
        raise ValueError("GCP_PROJECT_ID environment variable is required")
    
    try:
        from google.cloud import storage
        _storage_client = storage.Client(project=settings.gcp_project_id)
        logger.info(f"Cloud Storage client initialized for project: {settings.gcp_project_id}")
        return _storage_client
    except ImportError:
        raise ImportError("google-cloud-storage package is required for GCP backend")


def _encode_token(payload: Optional[dict[str, Any]]) -> Optional[str]:
    """Encode pagination token"""
    if not payload:
        return None
    raw = json.dumps(payload).encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def _decode_token(token: Optional[str]) -> Optional[dict[str, Any]]:
    """Decode pagination token"""
    if not token:
        return None
    try:
        raw = base64.b64decode(token.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("Invalid pagination token provided")
        return None


def _now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def _build_image_urls(keys: list[str]) -> Optional[list[str]]:
    """Build public URLs for Cloud Storage objects"""
    if not keys:
        return None
    if not settings.gcp_storage_bucket:
        raise ValueError("GCP_STORAGE_BUCKET environment variable is required")
    
    # Public URL format: https://storage.googleapis.com/BUCKET_NAME/OBJECT_NAME
    return [
        f"https://storage.googleapis.com/{settings.gcp_storage_bucket}/{key}"
        for key in keys
    ]


class GcpBackend(BackendBase):
    """GCP実装 (Firestore + Cloud Storage + Firebase Auth)"""
    
    def __init__(self):
        """Initialize GCP backend"""
        logger.info("Initializing GCP backend")
        # Clients are lazily initialized when first used
    
    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """List posts from Firestore"""
        try:
            from google.cloud import firestore
        except ImportError:
            raise ImportError("google-cloud-firestore is required for GCP backend")
        
        db = _get_firestore()
        posts_ref = db.collection(settings.gcp_posts_collection)
        
        # Order by createdAt DESC, then postId DESC for stable pagination
        query = posts_ref.order_by("createdAt", direction=firestore.Query.DESCENDING)
        query = query.order_by("postId", direction=firestore.Query.DESCENDING).limit(limit)
        
        # Handle pagination cursor
        cursor = _decode_token(next_token)
        if cursor and cursor.get("createdAt") and cursor.get("postId"):
            query = query.start_after({
                "createdAt": cursor["createdAt"],
                "postId": cursor["postId"]
            })
        
        try:
            docs = list(query.stream())
            logger.info(f"Found {len(docs)} posts in Firestore")
        except Exception as e:
            logger.error(f"Firestore query failed: {e}")
            raise
        
        posts: list[Post] = []
        for doc in docs:
            data = doc.to_dict() or {}
            
            # Handle image keys (may be list or single value)
            raw_image_keys = data.get("imageKeys")
            image_keys = raw_image_keys or ([] if data.get("imageKey") is None else [data.get("imageKey")])
            image_keys = [key for key in image_keys if isinstance(key, str)]
            
            post = Post(
                postId=data.get("postId"),
                userId=data.get("userId"),
                nickname=data.get("nickname"),
                content=data.get("content"),
                createdAt=data.get("createdAt"),
                updatedAt=data.get("updatedAt") or data.get("createdAt"),
                isMarkdown=data.get("isMarkdown"),
                tags=data.get("tags"),
                imageUrls=_build_image_urls(image_keys),
            )
            posts.append(post)
        
        # Client-side tag filtering (Firestore doesn't support array-contains with pagination)
        if tag:
            posts = [p for p in posts if p.tags and tag in p.tags]
        
        # Generate next token
        next_out = None
        if docs:
            last = docs[-1].to_dict() or {}
            next_out = _encode_token({
                "createdAt": last.get("createdAt"),
                "postId": last.get("postId")
            })
        
        return posts, next_out
    
    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """Create a new post in Firestore"""
        logger.info(f"Creating post for user {user.user_id}")
        
        db = _get_firestore()
        post_id = str(uuid.uuid4())
        created_at = _now_iso()
        
        # Get user's nickname from profile
        profile_doc = db.collection(settings.gcp_profiles_collection).document(user.user_id).get()
        profile = profile_doc.to_dict() if profile_doc.exists else None
        nickname = profile.get("nickname") if profile else None
        if not nickname:
            nickname = user.nickname
        
        # Build post document
        item: dict[str, Any] = {
            "postId": post_id,
            "userId": user.user_id,
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
        
        logger.info(f"Writing post {post_id} to Firestore collection {settings.gcp_posts_collection}")
        db.collection(settings.gcp_posts_collection).document(post_id).set(item)
        
        return {"item": item}
    
    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """Delete a post from Firestore"""
        db = _get_firestore()
        post_ref = db.collection(settings.gcp_posts_collection).document(post_id)
        doc = post_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Post not found: {post_id}")
        
        data = doc.to_dict() or {}
        
        # Check permissions
        if not user.is_admin and data.get("userId") != user.user_id:
            raise PermissionError("You do not have permission to delete this post")
        
        # Delete associated images from Cloud Storage
        image_keys = data.get("imageKeys") or ([] if data.get("imageKey") is None else [data.get("imageKey")])
        image_keys = [key for key in image_keys if isinstance(key, str)]
        
        if image_keys and settings.gcp_storage_bucket:
            storage_client = _get_storage()
            bucket = storage_client.bucket(settings.gcp_storage_bucket)
            for key in image_keys:
                try:
                    bucket.blob(key).delete()
                    logger.info(f"Deleted image: {key}")
                except Exception as e:
                    logger.error(f"Failed to delete image {key}: {e}")
        
        # Delete post document
        post_ref.delete()
        logger.info(f"Deleted post {post_id}")
        
        return {
            "status": "deleted",
            "post_id": post_id,
        }
    
    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        """Update a post in Firestore"""
        db = _get_firestore()
        post_ref = db.collection(settings.gcp_posts_collection).document(post_id)
        doc = post_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Post not found: {post_id}")
        
        data = doc.to_dict() or {}
        
        # Check permissions
        if not user.is_admin and data.get("userId") != user.user_id:
            raise PermissionError("You do not have permission to update this post")
        
        # Build update data
        now = _now_iso()
        update_data: dict[str, Any] = {
            "updatedAt": now,
        }
        
        if body.content is not None:
            update_data["content"] = body.content
        if body.tags is not None:
            update_data["tags"] = body.tags
        if body.image_keys is not None:
            update_data["imageKeys"] = body.image_keys
        
        # Update document
        post_ref.update(update_data)
        logger.info(f"Updated post {post_id}")
        
        return {
            "status": "updated",
            "post_id": post_id,
            "updated_at": now,
        }
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        """Get user profile from Firestore"""
        db = _get_firestore()
        doc = db.collection(settings.gcp_profiles_collection).document(user_id).get()
        
        if not doc.exists:
            return ProfileResponse(userId=user_id, nickname="")
        
        data = doc.to_dict() or {}
        
        return ProfileResponse(
            userId=user_id,
            nickname=data.get("nickname") or "",
            updatedAt=data.get("updatedAt"),
            createdAt=data.get("createdAt"),
        )
    
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """Update user profile in Firestore"""
        db = _get_firestore()
        now = _now_iso()
        profile_ref = db.collection(settings.gcp_profiles_collection).document(user.user_id)
        existing = profile_ref.get()
        
        # Preserve createdAt if exists
        created_at = now
        if existing.exists:
            created_at = (existing.to_dict() or {}).get("createdAt") or created_at
        
        item = {
            "userId": user.user_id,
            "nickname": body.nickname,
            "updatedAt": now,
            "createdAt": created_at,
            "docType": "profile",
        }
        profile_ref.set(item)
        logger.info(f"Updated profile for user {user.user_id}")
        
        return ProfileResponse(
            userId=user.user_id,
            nickname=body.nickname,
            updatedAt=now,
            createdAt=created_at,
        )
    
    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        """Generate signed URLs for Cloud Storage uploads"""
        if not settings.gcp_storage_bucket:
            raise ValueError("GCP_STORAGE_BUCKET environment variable is required")
        
        storage_client = _get_storage()
        bucket = storage_client.bucket(settings.gcp_storage_bucket)
        
        post_id = str(uuid.uuid4())
        content_type = "image/jpeg"  # Default content type
        
        urls = []
        for index in range(count):
            key = f"images/{post_id}-{index}-{secrets.token_hex(8)}.jpeg"
            blob = bucket.blob(key)
            
            # Generate signed URL
            # For Cloud Run with default credentials, we may need impersonated credentials
            generate_url_kwargs = {}
            if settings.gcp_service_account:
                try:
                    import google.auth
                    from google.auth import impersonated_credentials
                    
                    # Get default credentials
                    source_credentials, _ = google.auth.default()
                    
                    # Create impersonated credentials
                    signing_credentials = impersonated_credentials.Credentials(
                        source_credentials=source_credentials,
                        target_principal=settings.gcp_service_account,
                        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
                        lifetime=3600
                    )
                    generate_url_kwargs["credentials"] = signing_credentials
                except Exception as e:
                    logger.warning(f"Failed to create impersonated credentials: {e}")
            
            try:
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(seconds=settings.presigned_url_expiry),
                    method="PUT",
                    content_type=content_type,
                    **generate_url_kwargs,
                )
                urls.append({
                    "url": url,
                    "key": key,
                    "fields": {},
                })
                logger.info(f"Generated upload URL for key: {key}")
            except Exception as e:
                logger.error(f"Failed to generate signed URL: {e}")
                raise
        
        return urls
