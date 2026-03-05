import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo
from app.config import settings

logger = logging.getLogger(__name__)


class LocalBackend(BackendBase):
    """ローカル開発環境用バックエンド (PostgreSQL + MinIO/FS)"""
    
    def __init__(self):
        """初期化"""
        self.engine = None
        self.minio_client = None
        self._init_database()
        self._init_storage()
    
    def _init_database(self):
        """データベース接続を初期化"""
        if not settings.database_url:
            raise ValueError("DATABASE_URL is required for local backend")
        
        try:
            self.engine = create_engine(
                settings.database_url,
                poolclass=StaticPool,
                echo=settings.log_level == "DEBUG",
            )
            # 接続テスト
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _init_storage(self):
        """ストレージを初期化（MinIOまたはローカルFS）"""
        if settings.minio_endpoint:
            try:
                from minio import Minio
                # MinIOクライアント初期化
                endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
                self.minio_client = Minio(
                    endpoint,
                    access_key=settings.minio_access_key or "minioadmin",
                    secret_key=settings.minio_secret_key or "minioadmin",
                    secure=settings.minio_endpoint.startswith("https://"),
                )
                # バケット確認
                if not self.minio_client.bucket_exists(settings.minio_bucket):
                    self.minio_client.make_bucket(settings.minio_bucket)
                logger.info(f"MinIO storage initialized: {settings.minio_bucket}")
            except Exception as e:
                logger.warning(f"MinIO not available, using local filesystem: {e}")
                self.minio_client = None
        else:
            logger.info("Using local filesystem storage")
        
        # ローカルストレージディレクトリ作成
        storage_path = Path(settings.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self):
        """データベース接続を取得"""
        return self.engine.connect()
    
    def _build_image_urls(self, image_keys: list[str]) -> Optional[list[str]]:
        """画像キーからURLを生成"""
        if not image_keys:
            return None
        
        if self.minio_client:
            # MinIO URL
            endpoint = settings.minio_endpoint
            bucket = settings.minio_bucket
            return [f"{endpoint}/{bucket}/{key}" for key in image_keys]
        else:
            # ローカルファイルシステム URL (開発用)
            return [f"http://localhost:8000/storage/{key}" for key in image_keys]
    
    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """投稿一覧を取得"""
        with self._get_connection() as conn:
            # ベースクエリ
            query = """
                SELECT 
                    p.id, p.user_id, p.content, p.is_markdown,
                    p.image_keys, p.tags, p.created_at, p.updated_at,
                    prof.nickname
                FROM posts p
                LEFT JOIN profiles prof ON p.user_id = prof.user_id
            """
            
            params = {"limit": limit + 1}  # +1で次ページの有無を判定
            
            # タグフィルター
            if tag:
                query += " WHERE :tag = ANY(p.tags)"
                params["tag"] = tag
            
            # ページネーション
            if next_token:
                query += " AND " if tag else " WHERE "
                query += "p.created_at < :next_token"
                params["next_token"] = next_token
            
            query += " ORDER BY p.created_at DESC LIMIT :limit"
            
            result = conn.execute(text(query), params)
            rows = result.fetchall()
        
        # 結果を変換
        posts = []
        for row in rows[:limit]:  # limit件だけ返す
            post = Post(
                postId=row[0],
                userId=row[1],
                content=row[2],
                isMarkdown=row[3] or False,
                imageUrls=self._build_image_urls(row[4] or []),
                tags=row[5],
                createdAt=row[6].isoformat() if row[6] else datetime.now(timezone.utc).isoformat(),
                updatedAt=row[7].isoformat() if row[7] else None,
                nickname=row[8],
            )
            posts.append(post)
        
        # 次のページトークン
        output_next_token = None
        if len(rows) > limit:
            last_post = rows[limit - 1]
            output_next_token = last_post[6].isoformat() if last_post[6] else None
        
        return posts, output_next_token
    
    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """投稿を作成"""
        post_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        with self._get_connection() as conn:
            # プロフィールからニックネームを取得
            profile_query = text("SELECT nickname FROM profiles WHERE user_id = :user_id")
            profile_result = conn.execute(profile_query, {"user_id": user.user_id})
            profile_row = profile_result.fetchone()
            nickname = profile_row[0] if profile_row else None
            
            # 投稿を挿入
            insert_query = text("""
                INSERT INTO posts (id, user_id, content, is_markdown, image_keys, tags, created_at)
                VALUES (:id, :user_id, :content, :is_markdown, :image_keys, :tags, :created_at)
            """)
            
            conn.execute(
                insert_query,
                {
                    "id": post_id,
                    "user_id": user.user_id,
                    "content": body.content,
                    "is_markdown": body.is_markdown,
                    "image_keys": body.image_keys or [],
                    "tags": body.tags or [],
                    "created_at": created_at,
                },
            )
            conn.commit()
        
        return {
            "postId": post_id,
            "userId": user.user_id,
            "nickname": nickname,
            "content": body.content,
            "isMarkdown": body.is_markdown,
            "imageKeys": body.image_keys,
            "imageUrls": self._build_image_urls(body.image_keys or []),
            "tags": body.tags,
            "createdAt": created_at.isoformat(),
        }
    
    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """投稿を削除"""
        with self._get_connection() as conn:
            # 投稿の所有者確認
            check_query = text("SELECT user_id FROM posts WHERE id = :post_id")
            result = conn.execute(check_query, {"post_id": post_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found",
                )
            
            owner_id = row[0]
            if owner_id != user.user_id and not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own posts",
                )
            
            # 削除実行
            delete_query = text("DELETE FROM posts WHERE id = :post_id")
            conn.execute(delete_query, {"post_id": post_id})
            conn.commit()
        
        return {"message": "Post deleted successfully"}
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        """プロフィールを取得"""
        with self._get_connection() as conn:
            query = text("""
                SELECT user_id, nickname, bio, avatar_key, created_at, updated_at
                FROM profiles
                WHERE user_id = :user_id
            """)
            result = conn.execute(query, {"user_id": user_id})
            row = result.fetchone()
        
        if not row:
            # プロフィールが存在しない場合はデフォルトを返す
            return ProfileResponse(
                userId=user_id,
                nickname=None,
                bio=None,
                avatarUrl=None,
                createdAt=datetime.now(timezone.utc).isoformat(),
                updatedAt=None,
            )
        
        avatar_url = None
        if row[3]:  # avatar_key
            avatar_url = self._build_image_urls([row[3]])[0] if self._build_image_urls([row[3]]) else None
        
        return ProfileResponse(
            userId=row[0],
            nickname=row[1],
            bio=row[2],
            avatarUrl=avatar_url,
            createdAt=row[4].isoformat() if row[4] else None,
            updatedAt=row[5].isoformat() if row[5] else None,
        )
    
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """プロフィールを更新"""
        with self._get_connection() as conn:
            # UPSERTクエリ
            query = text("""
                INSERT INTO profiles (user_id, nickname, bio, avatar_key, created_at)
                VALUES (:user_id, :nickname, :bio, :avatar_key, :created_at)
                ON CONFLICT (user_id) DO UPDATE SET
                    nickname = COALESCE(:nickname, profiles.nickname),
                    bio = COALESCE(:bio, profiles.bio),
                    avatar_key = COALESCE(:avatar_key, profiles.avatar_key),
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            conn.execute(
                query,
                {
                    "user_id": user.user_id,
                    "nickname": body.nickname,
                    "bio": body.bio,
                    "avatar_key": body.avatar_key,
                    "created_at": datetime.now(timezone.utc),
                },
            )
            conn.commit()
        
        return self.get_profile(user.user_id)
    
    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        """画像アップロード用の署名付きURLを生成"""
        urls = []
        
        for _ in range(count):
            key = f"images/{user.user_id}/{uuid.uuid4()}.jpg"
            
            if self.minio_client:
                # MinIO署名付きURL
                try:
                    upload_url = self.minio_client.presigned_put_object(
                        settings.minio_bucket,
                        key,
                        expires=timedelta(seconds=settings.presigned_url_expiry),
                    )
                except Exception as e:
                    logger.error(f"Failed to generate MinIO presigned URL: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate upload URL",
                    )
            else:
                # ローカルファイルシステム用（実際のアップロードエンドポイントが必要）
                upload_url = f"http://localhost:8000/uploads/{key}"
            
            urls.append({
                "uploadUrl": upload_url,
                "key": key,
            })
        
        return urls
