"""AWS Backend Implementation with DynamoDB Single Table Design"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3

from app.auth import UserInfo
from app.backends.base import BackendBase
from app.models import (
    CreatePostBody,
    Post,
    ProfileResponse,
    ProfileUpdateRequest,
    UpdatePostBody,
)

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
            raise ValueError(
                "POSTS_TABLE_NAME environment variable is required")

        self.table = self.dynamodb.Table(self.table_name)
        self.presigned_expiry = int(os.environ.get("PRESIGNED_URL_EXPIRY", "3600"))

        logger.info(
            f"Initialized AwsBackend with table={self.table_name}, bucket={self.bucket_name}"
        )

    def _key_to_url(self, key: str) -> str:
        """S3キーをpresigned GETのURLに変換（有効期限1時間）"""
        if not key or key.startswith("http"):
            return key
        if not self.bucket_name:
            return key
        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=self.presigned_expiry,
            )
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL for {key}: {e}")
            return key

    def _get_nickname(self, user_id: str) -> Optional[str]:
        """DynamoDB PROFILESからニックネームを取得"""
        try:
            result = self.table.get_item(Key={"PK": "PROFILES", "SK": user_id})
            return result.get("Item", {}).get("nickname")
        except Exception:
            return None

    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
        user: Optional[UserInfo] = None,
    ) -> tuple[list[Post], Optional[str]]:
        """投稿一覧を取得 (DynamoDB Query)"""
        try:
            query_kwargs = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": "POSTS"},
                "ScanIndexForward": False,  # 降順 (新しい順)
                "Limit": limit,
            }

            if next_token:
                query_kwargs["ExclusiveStartKey"] = {
                    "PK": "POSTS", "SK": next_token}

            # タグフィルター
            if tag:
                query_kwargs["FilterExpression"] = "contains(tags, :tag)"
                query_kwargs["ExpressionAttributeValues"][":tag"] = tag

            response = self.table.query(**query_kwargs)

            posts = []
            for item in response.get("Items", []):
                # S3キーをpresigned URLに変換
                image_urls = [
                    self._key_to_url(k)
                    for k in item.get("imageUrls", [])
                ]
                posts.append(
                    Post(
                        postId=item["postId"],
                        userId=item["userId"],
                        nickname=item.get("nickname"),
                        content=item["content"],
                        tags=item.get("tags", []),
                        createdAt=item["createdAt"],
                        updatedAt=item.get("updatedAt"),
                        imageUrls=image_urls,
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

            # ニックネームをプロフィールから取得して投稿に保存（非正規化）
            nickname = self._get_nickname(user.user_id)

            image_keys = body.image_keys if body.image_keys else []
            item: dict = {
                "PK": "POSTS",
                "SK": now + "#" + post_id,  # タイムスタンプ + UUID
                "postId": post_id,
                "userId": user.user_id,
                "content": body.content,
                "tags": body.tags if body.tags else [],
                "createdAt": now,
                "updatedAt": now,
                "imageUrls": image_keys,
            }
            if nickname is not None:
                item["nickname"] = nickname

            self.table.put_item(Item=item)

            # レスポンス用にS3キーをpresigned URLに変換
            image_urls = [self._key_to_url(k) for k in image_keys]

            return {
                "post_id": post_id,
                "user_id": user.user_id,
                "nickname": nickname,
                "content": body.content,
                "tags": item["tags"],
                "created_at": now,
                "image_urls": image_urls,
            }

        except Exception as e:
            logger.error(f"Error creating post: {e}")
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
                raise PermissionError(
                    "You do not have permission to delete this post")

            # 削除
            self.table.delete_item(Key={"PK": "POSTS", "SK": item["SK"]})

            return {"status": "deleted", "post_id": post_id}

        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            raise

    def get_post(self, post_id: str) -> dict:
        """投稿を取得 (DynamoDB Query by postId)"""
        try:
            # postId から投稿を取得
            response = self.table.query(
                IndexName="PostIdIndex",
                KeyConditionExpression="postId = :postId",
                ExpressionAttributeValues={":postId": post_id},
            )

            if not response.get("Items"):
                raise ValueError(f"Post not found: {post_id}")

            item = response["Items"][0]

            # S3キーをpresigned URLに変換
            image_urls = [
                self._key_to_url(k) for k in item.get("imageUrls", [])
            ]

            # レスポンス形式を統一
            return {
                "id": item["postId"],
                "postId": item["postId"],
                "post_id": item["postId"],
                "userId": item.get("userId"),
                "user_id": item.get("userId"),
                "nickname": item.get("nickname"),
                "content": item.get("content"),
                "tags": item.get("tags", []),
                "createdAt": item.get("createdAt"),
                "created_at": item.get("createdAt"),
                "updatedAt": item.get("updatedAt"),
                "updated_at": item.get("updatedAt"),
                "imageUrls": image_urls,
                "image_urls": image_urls,
            }

        except Exception as e:
            logger.error(f"Error getting post: {e}")
            raise

    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        """投稿を更新 (DynamoDB UpdateItem)"""
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
                raise PermissionError(
                    "You do not have permission to update this post")

            # 更新
            now = datetime.now(timezone.utc).isoformat()
            update_expr = "SET updatedAt = :updatedAt"
            expr_values = {":updatedAt": now}

            if body.content is not None:
                update_expr += ", content = :content"
                expr_values[":content"] = body.content

            if body.tags is not None:
                update_expr += ", tags = :tags"
                expr_values[":tags"] = body.tags

            if body.image_keys is not None:
                update_expr += ", imageUrls = :imageUrls"
                expr_values[":imageUrls"] = body.image_keys

            self.table.update_item(
                Key={"PK": "POSTS", "SK": item["SK"]},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
            )

            return {
                "status": "updated",
                "post_id": post_id,
                "updated_at": now,
            }

        except Exception as e:
            logger.error(f"Error updating post: {e}")
            raise

    def get_profile(self, user_id: str) -> ProfileResponse:
        """プロフィールを取得"""
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
        """プロフィールを更新"""
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

    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        """画像アップロード用の署名付きURLを生成"""
        if not self.bucket_name:
            raise ValueError("IMAGES_BUCKET_NAME not configured")

        urls = []
        for _ in range(count):
            image_id = str(uuid.uuid4())
            key = f"{user.user_id}/{image_id}.jpg"

            # 署名付きURLを生成 (PUT用)
            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": "image/jpeg",
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

    def like_post(self, post_id: str, user: UserInfo) -> dict:
        """いいね機能（未実装）"""
        return {"post_id": post_id, "liked": True}

    def unlike_post(self, post_id: str, user: UserInfo) -> dict:
        """いいね取り消し機能（未実装）"""
        return {"post_id": post_id, "liked": False}
