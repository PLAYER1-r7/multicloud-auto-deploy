"""AWS Backend Implementation with DynamoDB Single Table Design"""

import os
import boto3
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from decimal import Decimal
import logging

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo

logger = logging.getLogger(__name__)


class AwsBackend(BackendBase):
    """AWS実装 (DynamoDB Single Table Design + S3 + Cognito)"""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.s3_client = boto3.client("s3")

        # 環境変数から設定を取得
        self.table_name = os.environ.get("POSTS_TABLE_NAME", "")
        self.bucket_name = os.environ.get("IMAGES_BUCKET_NAME", "")

        if not self.table_name:
            raise ValueError("POSTS_TABLE_NAME environment variable is required")

        self.table = self.dynamodb.Table(self.table_name)
        logger.info(
            f"Initialized AwsBackend with table={self.table_name}, bucket={self.bucket_name}"
        )

    def _key_to_presigned_url(self, key: str) -> str:
        """S3キーを署名付きGET URLに変換 (1時間有効)"""
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=3600,
        )

    def _resolve_image_urls(self, keys: list) -> list[str]:
        """キーリストを署名付きURLに変換 (既にURLの場合はそのまま返す)"""
        if not self.bucket_name or not keys:
            return []
        result = []
        for k in keys:
            if k and isinstance(k, str):
                if k.startswith("http"):
                    result.append(k)
                else:
                    try:
                        result.append(self._key_to_presigned_url(k))
                    except Exception as e:
                        logger.warning(f"Failed to generate presigned URL for {k}: {e}")
        return result

    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """投稿一覧を取得 (DynamoDB Query)"""
        try:
            query_kwargs = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": "POSTS"},
                "ScanIndexForward": False,  # 降順 (新しい順)
                "Limit": limit,
            }

            if next_token:
                query_kwargs["ExclusiveStartKey"] = {"PK": "POSTS", "SK": next_token}

            # タグフィルター
            if tag:
                query_kwargs["FilterExpression"] = "contains(tags, :tag)"
                query_kwargs["ExpressionAttributeValues"][":tag"] = tag

            response = self.table.query(**query_kwargs)

            posts = []
            for item in response.get("Items", []):
                raw_urls = item.get("imageKeys") or item.get("imageUrls") or []
                posts.append(
                    Post(
                        postId=item["postId"],
                        userId=item["userId"],
                        nickname=item.get("nickname"),
                        content=item["content"],
                        tags=item.get("tags", []),
                        createdAt=item["createdAt"],
                        updatedAt=item.get("updatedAt"),
                        imageUrls=self._resolve_image_urls(raw_urls),
                    )
                )

            # ページネーショントークン
            next_token = None
            if "LastEvaluatedKey" in response:
                next_token = response["LastEvaluatedKey"]["SK"]

            return posts, next_token

        except Exception as e:
            logger.error(f"Error listing posts: {e}")
            raise

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """投稿を作成 (DynamoDB PutItem)"""
        try:
            post_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            # プロフィールからnicknameを取得
            nickname = None
            try:
                profile_item = self.table.get_item(
                    Key={"PK": "PROFILES", "SK": user.user_id}
                ).get("Item")
                if profile_item:
                    nickname = profile_item.get("nickname")
            except Exception as e:
                logger.warning(f"Failed to fetch nickname for {user.user_id}: {e}")

            image_keys = body.image_keys if body.image_keys else []

            item = {
                "PK": "POSTS",
                "SK": now + "#" + post_id,  # タイムスタンプ + UUID
                "postId": post_id,
                "userId": user.user_id,
                "nickname": nickname,
                "content": body.content,
                "tags": body.tags if body.tags else [],
                "createdAt": now,
                "updatedAt": now,
                "imageKeys": image_keys,  # 生のS3キーを保存
            }

            self.table.put_item(Item=item)

            presigned_urls = self._resolve_image_urls(image_keys)

            return {
                "postId": post_id,
                "userId": user.user_id,
                "nickname": nickname,
                "content": body.content,
                "tags": item["tags"],
                "createdAt": now,
                "imageUrls": presigned_urls,
                # snake_case aliases
                "post_id": post_id,
                "user_id": user.user_id,
                "created_at": now,
                "image_urls": presigned_urls,
            }

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise

    def get_post(self, post_id: str):
        """投稿を1件取得 (PostIdIndex で検索)"""
        try:
            response = self.table.query(
                IndexName="PostIdIndex",
                KeyConditionExpression="postId = :postId",
                ExpressionAttributeValues={":postId": post_id},
            )
            items = response.get("Items", [])
            if not items:
                return None
            item = items[0]
            raw_urls = item.get("imageKeys") or item.get("imageUrls") or []
            return Post(
                postId=item["postId"],
                userId=item["userId"],
                nickname=item.get("nickname"),
                content=item["content"],
                tags=item.get("tags", []),
                createdAt=item["createdAt"],
                updatedAt=item.get("updatedAt"),
                imageUrls=self._resolve_image_urls(raw_urls),
            )
        except Exception as e:
            logger.error(f"Error getting post {post_id}: {e}")
            raise

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """投稿を削除 (DynamoDB DeleteItem)"""
        try:
            # まず postId から SK を取得
            response = self.table.query(
                IndexName="PostIdIndex",
                KeyConditionExpression="postId = :postId",
                ExpressionAttributeValues={":postId": post_id},
            )

            if not response.get("Items"):
                raise ValueError(f"Post not found: {post_id}")

            item = response["Items"][0]

            # ユーザー権限チェック
            if item["userId"] != user.user_id and not user.is_admin:
                raise PermissionError("You do not have permission to delete this post")

            # 削除
            self.table.delete_item(Key={"PK": "POSTS", "SK": item["SK"]})

            return {"status": "deleted", "post_id": post_id}

        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            raise

    def get_profile(self, user_id: str) -> ProfileResponse:
        """プロフィールを取得 (DynamoDB)"""
        try:
            result = self.table.get_item(
                Key={"PK": "PROFILES", "SK": user_id}
            )
            item = result.get("Item")
            if not item:
                return ProfileResponse(
                    user_id=user_id,
                    nickname=None,
                    bio=None,
                    avatar_url=None,
                )
            return ProfileResponse(
                user_id=user_id,
                nickname=item.get("nickname"),
                bio=item.get("bio"),
                avatar_url=item.get("avatar_url"),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
            )
        except Exception as e:
            logger.error(f"Error getting profile for {user_id}: {e}")
            raise

    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """プロフィールを更新 (DynamoDB)"""
        now = datetime.now(timezone.utc).isoformat()

        # 既存プロフィールを取得して created_at を保持し、未指定フィールドをマージ
        existing = self.table.get_item(
            Key={"PK": "PROFILES", "SK": user.user_id}
        ).get("Item")
        created_at = existing.get("created_at", now) if existing else now

        item: dict = {
            "PK": "PROFILES",
            "SK": user.user_id,
            "user_id": user.user_id,
            "created_at": created_at,
            "updated_at": now,
        }
        # 既存データをベースにしてリクエストで指定されたフィールドのみ上書き
        if existing:
            for field in ("nickname", "bio", "avatar_url"):
                if field in existing:
                    item[field] = existing[field]
        if body.nickname is not None:
            item["nickname"] = body.nickname
        if body.bio is not None:
            item["bio"] = body.bio
        if body.avatar_key is not None:
            item["avatar_url"] = body.avatar_key

        try:
            self.table.put_item(Item=item)
        except Exception as e:
            logger.error(f"Error updating profile for {user.user_id}: {e}")
            raise

        return ProfileResponse(
            user_id=user.user_id,
            nickname=item.get("nickname"),
            bio=item.get("bio"),
            avatar_url=item.get("avatar_url"),
            created_at=created_at,
            updated_at=now,
        )

    def generate_upload_urls(
        self,
        count: int,
        user: UserInfo,
        content_types: Optional[list[str]] = None,
    ) -> list[dict[str, str]]:
        """画像アップロード用の署名付きURLを生成"""
        if not self.bucket_name:
            raise ValueError("IMAGES_BUCKET_NAME not configured")

        ext_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/heic": "heic",
            "image/heif": "heif",
        }

        urls = []
        for i in range(count):
            ct = (
                content_types[i]
                if content_types and i < len(content_types)
                else None
            ) or "image/jpeg"
            ext = ext_map.get(ct, "jpg")
            image_id = str(uuid.uuid4())
            key = f"{user.user_id}/{image_id}.{ext}"

            # 署名付きURLを生成 (PUT用)
            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": ct,
                },
                ExpiresIn=3600,  # 1時間
            )

            urls.append(
                {
                    "url": presigned_url,
                    "key": key,
                }
            )

        return urls
