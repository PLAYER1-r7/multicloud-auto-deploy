"""GCP Backend Implementation using Firestore + Cloud Storage"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.auth import UserInfo
from app.backends.base import BackendBase
from app.config import settings
from app.models import CreatePostBody, Post, ProfileResponse, ProfileUpdateRequest

logger = logging.getLogger(__name__)

try:
    import google.auth
    import google.auth.transport.requests
    from google.cloud import firestore, storage

    _gcp_available = True
except ImportError:
    _gcp_available = False
    logger.warning("google-cloud-firestore/storage not available")


class GcpBackend(BackendBase):
    """GCP実装 (Firestore + Cloud Storage + Firebase Auth)"""

    def __init__(self):
        if not _gcp_available:
            raise ImportError(
                "google-cloud-firestore and google-cloud-storage are required"
            )

        project_id = settings.gcp_project_id
        self.db = firestore.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)

        self.posts_collection = settings.gcp_posts_collection
        self.profiles_collection = settings.gcp_profiles_collection
        self.bucket_name = settings.gcp_storage_bucket or f"{project_id}-uploads"

        # GCS 署名付きURL用: 認証情報をキャッシュ（毎リクエストのメタデータサーバー呼び出し回避）
        # generate_upload_urls で credentials.valid をチェックし、期限切れ時のみ refresh する
        try:
            self._gcs_credentials, _ = google.auth.default()
            self._gcs_auth_request = google.auth.transport.requests.Request()
        except Exception as e:
            logger.warning("Could not pre-fetch GCS credentials at init: %r", e)
            self._gcs_credentials = None
            self._gcs_auth_request = None

        # settings を __init__ でキャッシュ（テスト時のパッチ有効期間の問題を回避）
        self._service_account = settings.gcp_service_account
        self._presigned_url_expiry = getattr(settings, "presigned_url_expiry", 300)

        logger.info(
            f"GcpBackend initialized: project={project_id}, "
            f"posts={self.posts_collection}, profiles={self.profiles_collection}, "
            f"bucket={self.bucket_name}"
        )

    def _doc_to_post(self, doc) -> Post:
        """FirestoreドキュメントをPostモデルに変換"""
        data = doc.to_dict()

        # Firestore Timestamp → ISO文字列
        def ts_to_str(ts) -> str | None:
            if ts is None:
                return None
            if hasattr(ts, "isoformat"):
                return ts.isoformat()
            if hasattr(ts, "timestamp"):
                return datetime.fromtimestamp(
                    ts.timestamp(), tz=timezone.utc
                ).isoformat()
            return str(ts)

        return Post(
            postId=data.get("postId", doc.id),
            userId=data.get("userId", "unknown"),
            nickname=data.get("nickname"),
            content=data.get("content", ""),
            isMarkdown=data.get("isMarkdown", False),
            imageUrls=data.get("imageUrls", []),
            tags=data.get("tags", []),
            createdAt=ts_to_str(data.get("createdAt"))
            or datetime.now(timezone.utc).isoformat(),
            updatedAt=ts_to_str(data.get("updatedAt")),
        )

    def list_posts(
        self,
        limit: int,
        next_token: str | None,
        tag: str | None,
    ) -> tuple[list[Post], str | None]:
        """Firestore から投稿一覧を取得"""
        try:
            col = self.db.collection(self.posts_collection)
            query = col.order_by(
                "createdAt", direction=firestore.Query.DESCENDING
            ).limit(limit + 1)

            if next_token:
                # next_token はドキュメントIDとして使用
                cursor_doc = col.document(next_token).get()
                if cursor_doc.exists:
                    query = query.start_after(cursor_doc)

            if tag:
                query = query.where(
                    filter=firestore.FieldFilter("tags", "array_contains", tag)
                )

            docs = list(query.stream())

            output_next_token = None
            if len(docs) > limit:
                docs = docs[:limit]
                output_next_token = docs[-1].id

            posts = [self._doc_to_post(doc) for doc in docs]
            return posts, output_next_token

        except Exception as e:
            logger.error("Error listing posts from Firestore: %r", e)
            raise

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """Firestoreに投稿を作成"""
        try:
            post_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            now_str = now.isoformat()

            # プロフィールからnicknameを取得
            nickname = None
            try:
                profile_doc = (
                    self.db.collection(self.profiles_collection)
                    .document(user.user_id)
                    .get()
                )
                if profile_doc.exists:
                    nickname = profile_doc.to_dict().get("nickname")
            except Exception as e:
                logger.warning("Failed to fetch nickname for %r: %r", user.user_id, e)

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
                "nickname": nickname,
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
                nickname=nickname,
                content=body.content,
                isMarkdown=body.is_markdown,
                imageUrls=image_urls,
                tags=body.tags or [],
                createdAt=now_str,
            ).model_dump()

        except Exception as e:
            logger.error("Error creating post in Firestore: %r", e)
            raise

    def get_post(self, post_id: str):
        """Firestoreから投稿を1件取得"""
        try:
            doc = self.db.collection(self.posts_collection).document(post_id).get()
            if not doc.exists:
                return None
            item = doc.to_dict()
            from app.models import Post

            return Post(
                postId=post_id,
                userId=item["userId"],
                nickname=item.get("nickname"),
                content=item["content"],
                tags=item.get("tags") or [],
                createdAt=item["createdAt"],
                updatedAt=item.get("updatedAt"),
                imageUrls=item.get("imageUrls") or [],
            )
        except Exception as e:
            logger.error("Error getting post %r: %r", post_id, e)
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
            if data.get("userId") != user.user_id and not user.is_admin:
                from fastapi import HTTPException

                raise HTTPException(status_code=403, detail="Not authorized")

            doc_ref.delete()
            logger.info("Deleted post %r", post_id)
            return {"message": "Post deleted successfully", "postId": post_id}

        except Exception as e:
            logger.error("Error deleting post %r from Firestore: %r", post_id, e)
            raise

    def get_profile(self, user_id: str) -> ProfileResponse:
        """Firestoreからプロフィールを取得"""
        try:
            doc_ref = self.db.collection(self.profiles_collection).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return ProfileResponse(userId=user_id)

            data = doc.to_dict()

            def ts_to_str(ts) -> str | None:
                if ts is None:
                    return None
                if hasattr(ts, "isoformat"):
                    return ts.isoformat()
                if hasattr(ts, "timestamp"):
                    return datetime.fromtimestamp(
                        ts.timestamp(), tz=timezone.utc
                    ).isoformat()
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
            logger.error("Error getting profile %r from Firestore: %r", user_id, e)
            raise

    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """Firestoreのプロフィールを更新"""
        try:
            doc_ref = self.db.collection(self.profiles_collection).document(
                user.user_id
            )
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
            logger.error("Error updating profile %r in Firestore: %r", user.user_id, e)
            raise

    def generate_upload_urls(
        self,
        count: int,
        user: UserInfo,
        content_types: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Cloud Storage の署名付きURLを生成"""
        ext_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/heic": "heic",
            "image/heif": "heif",
        }
        try:
            # Cloud Functions / Cloud Run は Compute Engine 認証情報(トークンのみ)を持つ。
            # generate_signed_url には秘密鍵が必要なため、service_account_email と
            # access_token を渡し、IAM signBlob API 経由で署名する方式を使用する。
            # 認証情報は __init__ でキャッシュ済み。トークン期限切れ時のみ refresh する。
            credentials = self._gcs_credentials
            auth_request = self._gcs_auth_request
            if credentials is None or auth_request is None:
                # フォールバック: 初期化失敗時
                credentials, _ = google.auth.default()
                auth_request = google.auth.transport.requests.Request()
                self._gcs_credentials = credentials
                self._gcs_auth_request = auth_request

            # token が未取得または期限切れの場合のみ refresh（1時間に1回程度）
            if not getattr(credentials, "valid", True):
                credentials.refresh(auth_request)

            access_token = credentials.token
            # __init__ でキャッシュした値を使用
            sa_email = self._service_account
            if not sa_email:
                raise RuntimeError("GCP_SERVICE_ACCOUNT env var is not set")

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
                    expiration=timedelta(seconds=self._presigned_url_expiry),
                    method="PUT",
                    content_type=ct,
                    service_account_email=sa_email,
                    access_token=access_token,
                )
                urls.append({"url": upload_url, "key": key})

            return urls

        except Exception as e:
            logger.error("Error generating upload URLs for GCS: %r", e)
            raise
