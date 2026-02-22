"""GCP Backend Implementation using Firestore + Cloud Storage"""

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
    from google.cloud import firestore, storage
    _gcp_available = True
except ImportError:
    _gcp_available = False
    logger.warning("google-cloud-firestore/storage not available")


class GcpBackend(BackendBase):
    """GCP実装 (Firestore + Cloud Storage + Firebase Auth)"""

    def __init__(self):
        if not _gcp_available:
            raise ImportError("google-cloud-firestore and google-cloud-storage are required")

        project_id = settings.gcp_project_id
        self.db = firestore.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)

        self.posts_collection = settings.gcp_posts_collection
        self.profiles_collection = settings.gcp_profiles_collection
        self.bucket_name = settings.gcp_storage_bucket or f"{project_id}-uploads"

        logger.info(
            f"GcpBackend initialized: project={project_id}, "
            f"posts={self.posts_collection}, profiles={self.profiles_collection}, "
            f"bucket={self.bucket_name}"
        )

    def _doc_to_post(self, doc) -> Post:
        """FirestoreドキュメントをPostモデルに変換"""
        data = doc.to_dict()

        # Firestore Timestamp → ISO文字列
        def ts_to_str(ts) -> Optional[str]:
            if ts is None:
                return None
            if hasattr(ts, "isoformat"):
                return ts.isoformat()
            if hasattr(ts, "timestamp"):
                return datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc).isoformat()
            return str(ts)

        return Post(
            postId=data.get("postId", doc.id),
            userId=data.get("userId", "unknown"),
            content=data.get("content", ""),
            isMarkdown=data.get("isMarkdown", False),
            imageUrls=data.get("imageUrls", []),
            tags=data.get("tags", []),
            createdAt=ts_to_str(data.get("createdAt")) or datetime.now(timezone.utc).isoformat(),
            updatedAt=ts_to_str(data.get("updatedAt")),
        )

    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """Firestore から投稿一覧を取得"""
        try:
            col = self.db.collection(self.posts_collection)
            query = col.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit + 1)

            if next_token:
                # next_token はドキュメントIDとして使用
                cursor_doc = col.document(next_token).get()
                if cursor_doc.exists:
                    query = query.start_after(cursor_doc)

            if tag:
                query = query.where(filter=firestore.FieldFilter("tags", "array_contains", tag))

            docs = list(query.stream())

            output_next_token = None
            if len(docs) > limit:
                docs = docs[:limit]
                output_next_token = docs[-1].id

            posts = [self._doc_to_post(doc) for doc in docs]
            return posts, output_next_token

        except Exception as e:
            logger.error(f"Error listing posts from Firestore: {e}")
            raise

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """Firestoreに投稿を作成"""
        try:
            post_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            now_str = now.isoformat()

            # 画像キーをURLに変換
            image_urls = []
            if body.image_keys:
                image_urls = [
                    f"https://storage.googleapis.com/{self.bucket_name}/{key}"
                    for key in body.image_keys
                ]

            doc_data = {
                "postId": post_id,
                "userId": user.user_id,
                "content": body.content,
                "isMarkdown": body.is_markdown,
                "imageUrls": image_urls,
                "tags": body.tags or [],
                "createdAt": now_str,
                "updatedAt": None,
            }

            self.db.collection(self.posts_collection).document(post_id).set(doc_data)
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
            logger.error(f"Error creating post in Firestore: {e}")
            raise

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """Firestoreから投稿を削除"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()

            if not doc.exists:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Post not found")

            data = doc.to_dict()
            if data.get("userId") != user.user_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Not authorized")

            doc_ref.delete()
            logger.info(f"Deleted post {post_id}")
            return {"message": "Post deleted successfully", "postId": post_id}

        except Exception as e:
            logger.error(f"Error deleting post {post_id} from Firestore: {e}")
            raise

    def get_profile(self, user_id: str) -> ProfileResponse:
        """Firestoreからプロフィールを取得"""
        try:
            doc_ref = self.db.collection(self.profiles_collection).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return ProfileResponse(userId=user_id)

            data = doc.to_dict()

            def ts_to_str(ts) -> Optional[str]:
                if ts is None:
                    return None
                if hasattr(ts, "isoformat"):
                    return ts.isoformat()
                if hasattr(ts, "timestamp"):
                    return datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc).isoformat()
                return str(ts)

            return ProfileResponse(
                userId=user_id,
                nickname=data.get("nickname"),
                bio=data.get("bio"),
                avatarUrl=data.get("avatarUrl"),
                createdAt=ts_to_str(data.get("createdAt")),
                updatedAt=ts_to_str(data.get("updatedAt")),
            )

        except Exception as e:
            logger.error(f"Error getting profile {user_id} from Firestore: {e}")
            raise

    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """Firestoreのプロフィールを更新"""
        try:
            doc_ref = self.db.collection(self.profiles_collection).document(user.user_id)
            now_str = datetime.now(timezone.utc).isoformat()

            update_data: dict = {"updatedAt": now_str}
            if body.nickname is not None:
                update_data["nickname"] = body.nickname
            if body.bio is not None:
                update_data["bio"] = body.bio
            if body.avatar_key is not None:
                update_data["avatarUrl"] = (
                    f"https://storage.googleapis.com/{self.bucket_name}/{body.avatar_key}"
                )

            doc = doc_ref.get()
            if not doc.exists:
                update_data["createdAt"] = now_str
                update_data["userId"] = user.user_id
                doc_ref.set(update_data)
            else:
                doc_ref.update(update_data)

            return self.get_profile(user.user_id)

        except Exception as e:
            logger.error(f"Error updating profile {user.user_id} in Firestore: {e}")
            raise

    def generate_upload_urls(
        self,
        count: int,
        user: UserInfo,
        content_types: Optional[list[str]] = None,
    ) -> list[dict[str, str]]:
        """Cloud Storage の署名付きURLを生成"""
        ext_map = {
            "image/jpeg": "jpg", "image/jpg": "jpg",
            "image/png": "png", "image/gif": "gif",
            "image/webp": "webp", "image/heic": "heic", "image/heif": "heif",
        }
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            urls = []

            for i in range(count):
                ct = (
                    content_types[i]
                    if content_types and i < len(content_types)
                    else None
                ) or "image/jpeg"
                ext = ext_map.get(ct, "jpg")
                key = f"images/{user.user_id}/{uuid.uuid4()}.{ext}"
                blob = bucket.blob(key)
                upload_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(seconds=settings.presigned_url_expiry),
                    method="PUT",
                    content_type=ct,
                )
                urls.append({"url": upload_url, "key": key})

            return urls

        except Exception as e:
            logger.error(f"Error generating upload URLs for GCS: {e}")
            raise
