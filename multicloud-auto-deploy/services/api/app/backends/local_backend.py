"""Local Development Backend — DynamoDB Local + MinIO

Uses the same Single-Table Design as AwsBackend so that bugs found locally
behave identically in the cloud AWS environment.

Table: simple-sns-local  (configured via DYNAMODB_TABLE_NAME)
GSI:   PostIdIndex        (hash key: postId, projection: ALL)

Item types:
  Post    PK=POSTS          SK=<ISO timestamp>#<uuid>
  Profile PK=USER#<userId>  SK=PROFILE
          postId=PROFILE#<userId>  (used by PostIdIndex for profile lookups)
"""

import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, UpdatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo
from app.config import settings

logger = logging.getLogger(__name__)

_POSTS_PK = "POSTS"


class LocalBackend(BackendBase):
    """ローカル開発環境用バックエンド (DynamoDB Local + MinIO)"""

    def __init__(self):
        self._init_dynamodb()
        self._init_storage()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_dynamodb(self):
        """DynamoDB Local への接続を初期化し、テーブルを自動作成する"""
        endpoint = settings.dynamodb_endpoint or "http://localhost:8001"
        table_name = settings.dynamodb_table_name or "simple-sns-local"

        self.dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "local"),
            aws_secret_access_key=os.environ.get(
                "AWS_SECRET_ACCESS_KEY", "local"),
            region_name=settings.aws_region or "ap-northeast-1",
        )
        self.table_name = table_name
        self._ensure_table()
        self.table = self.dynamodb.Table(table_name)
        logger.info(
            f"DynamoDB Local connected: endpoint={endpoint}, table={table_name}")

    def _ensure_table(self):
        """テーブルが存在しなければ作成する（PostIdIndex GSI 付き）"""
        client = self.dynamodb.meta.client
        try:
            client.describe_table(TableName=self.table_name)
            logger.info(f"Table '{self.table_name}' already exists")
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
            logger.info(f"Creating table '{self.table_name}' ...")
            client.create_table(
                TableName=self.table_name,
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                    {"AttributeName": "postId", "AttributeType": "S"},
                ],
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "PostIdIndex",
                        "KeySchema": [
                            {"AttributeName": "postId", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    }
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            )
            # waiter は DynamoDB Local で動作しないため polling で代替
            for _ in range(20):
                time.sleep(0.5)
                try:
                    client.describe_table(TableName=self.table_name)
                    break
                except ClientError:
                    pass
            logger.info(f"Table '{self.table_name}' created")

    def _init_storage(self):
        """MinIO クライアントを初期化する（失敗時はローカル FS にフォールバック）"""
        self.minio_client = None
        if not settings.minio_endpoint:
            logger.info("MINIO_ENDPOINT not set — using local filesystem URLs")
            return
        try:
            from minio import Minio

            endpoint = (
                settings.minio_endpoint
                .replace("http://", "")
                .replace("https://", "")
            )
            self.minio_client = Minio(
                endpoint,
                access_key=settings.minio_access_key or "minioadmin",
                secret_key=settings.minio_secret_key or "minioadmin",
                secure=settings.minio_endpoint.startswith("https://"),
            )
            bucket = settings.minio_bucket
            if not self.minio_client.bucket_exists(bucket):
                self.minio_client.make_bucket(bucket)
            logger.info(f"MinIO storage initialised: bucket={bucket}")
        except Exception as exc:
            logger.warning(
                f"MinIO not available, falling back to local FS: {exc}")
            self.minio_client = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_image_urls(self, image_keys: list[str]) -> Optional[list[str]]:
        if not image_keys:
            return None
        # /storage/ プロキシ経由でブラウザからアクセス (ホスト非依存の相対 URL)
        bucket = settings.minio_bucket
        return [f"/storage/{bucket}/{k}" for k in image_keys]

    def _item_to_post(self, item: dict) -> Post:
        return Post(
            postId=item["postId"],
            userId=item.get("userId", ""),
            content=item.get("content", ""),
            isMarkdown=bool(item.get("isMarkdown", False)),
            tags=list(item.get("tags", [])),
            imageUrls=self._build_image_urls(list(item.get("imageKeys", []))),
            createdAt=item.get("createdAt", ""),
            updatedAt=item.get("updatedAt"),
            nickname=item.get("nickname"),
        )

    def _get_nickname(self, user_id: str) -> Optional[str]:
        try:
            res = self.table.query(
                IndexName="PostIdIndex",
                KeyConditionExpression="postId = :pid",
                ExpressionAttributeValues={":pid": f"PROFILE#{user_id}"},
            )
            items = res.get("Items", [])
            return items[0].get("nickname") if items else None
        except Exception:
            return None

    def _get_post_item_by_id(self, post_id: str) -> dict:
        """GSI で postId から DynamoDB アイテムを取得"""
        response = self.table.query(
            IndexName="PostIdIndex",
            KeyConditionExpression="postId = :pid",
            ExpressionAttributeValues={":pid": post_id},
        )
        items = response.get("Items", [])
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        return items[0]

    # ------------------------------------------------------------------
    # BackendBase implementation
    # ------------------------------------------------------------------

    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """投稿一覧を取得（PK=POSTS, 降順）"""
        kwargs: dict = {
            "KeyConditionExpression": "PK = :pk",
            "ExpressionAttributeValues": {":pk": _POSTS_PK},
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if next_token:
            kwargs["ExclusiveStartKey"] = {"PK": _POSTS_PK, "SK": next_token}
        if tag:
            kwargs["FilterExpression"] = "contains(tags, :tag)"
            kwargs["ExpressionAttributeValues"][":tag"] = tag

        response = self.table.query(**kwargs)
        items = response.get("Items", [])

        # プロフィール（ニックネーム）をまとめて取得
        user_ids = list({item.get("userId")
                        for item in items if item.get("userId")})
        nicknames: dict[str, Optional[str]] = {}
        for uid in user_ids:
            nicknames[uid] = self._get_nickname(uid)

        posts = []
        for item in items:
            item["nickname"] = nicknames.get(item.get("userId"))
            posts.append(self._item_to_post(item))

        output_next_token = None
        if "LastEvaluatedKey" in response:
            output_next_token = response["LastEvaluatedKey"]["SK"]

        return posts, output_next_token

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """投稿を作成"""
        post_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        item = {
            "PK": _POSTS_PK,
            "SK": f"{now}#{post_id}",
            "postId": post_id,
            "userId": user.user_id,
            "content": body.content,
            "isMarkdown": body.is_markdown or False,
            "tags": body.tags or [],
            "imageKeys": body.image_keys or [],
            "createdAt": now,
            "updatedAt": now,
        }
        self.table.put_item(Item=item)

        return {
            "postId": post_id,
            "userId": user.user_id,
            "nickname": self._get_nickname(user.user_id),
            "content": body.content,
            "isMarkdown": body.is_markdown or False,
            "imageKeys": body.image_keys,
            "imageUrls": self._build_image_urls(body.image_keys or []),
            "tags": body.tags,
            "createdAt": now,
        }

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """投稿を削除"""
        item = self._get_post_item_by_id(post_id)
        if item["userId"] != user.user_id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own posts",
            )
        self.table.delete_item(Key={"PK": _POSTS_PK, "SK": item["SK"]})
        return {"message": "Post deleted successfully"}

    def get_post(self, post_id: str) -> dict:
        """投稿を取得"""
        item = self._get_post_item_by_id(post_id)
        return {
            "postId": item["postId"],
            "userId": item.get("userId"),
            "content": item.get("content"),
            "isMarkdown": bool(item.get("isMarkdown", False)),
            "tags": list(item.get("tags", [])),
            "imageUrls": self._build_image_urls(list(item.get("imageKeys", []))),
            "createdAt": item.get("createdAt"),
            "updatedAt": item.get("updatedAt"),
            "nickname": self._get_nickname(item.get("userId", "")),
        }

    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        """投稿を更新"""
        item = self._get_post_item_by_id(post_id)
        if item["userId"] != user.user_id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own posts",
            )
        now = datetime.now(timezone.utc).isoformat()
        update_expr = "SET updatedAt = :now"
        expr_values: dict = {":now": now}

        if body.content is not None:
            update_expr += ", content = :content"
            expr_values[":content"] = body.content
        if getattr(body, "is_markdown", None) is not None:
            update_expr += ", isMarkdown = :isMarkdown"
            expr_values[":isMarkdown"] = body.is_markdown
        if body.tags is not None:
            update_expr += ", tags = :tags"
            expr_values[":tags"] = body.tags

        self.table.update_item(
            Key={"PK": _POSTS_PK, "SK": item["SK"]},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
        )
        return self.get_post(post_id)

    def get_profile(self, user_id: str) -> ProfileResponse:
        """プロフィールを取得"""
        try:
            response = self.table.query(
                IndexName="PostIdIndex",
                KeyConditionExpression="postId = :pid",
                ExpressionAttributeValues={":pid": f"PROFILE#{user_id}"},
            )
            items = response.get("Items", [])
        except Exception as exc:
            logger.error(f"Failed to get profile for {user_id}: {exc}")
            items = []

        if not items:
            return ProfileResponse(
                userId=user_id,
                nickname=None,
                bio=None,
                avatarUrl=None,
                createdAt=datetime.now(timezone.utc).isoformat(),
                updatedAt=None,
            )

        item = items[0]
        avatar_url = None
        if item.get("avatarKey"):
            urls = self._build_image_urls([item["avatarKey"]])
            avatar_url = urls[0] if urls else None

        return ProfileResponse(
            userId=item.get("userId", user_id),
            nickname=item.get("nickname"),
            bio=item.get("bio"),
            avatarUrl=avatar_url,
            createdAt=item.get("createdAt", ""),
            updatedAt=item.get("updatedAt"),
        )

    def update_profile(self, user: UserInfo, body: ProfileUpdateRequest) -> ProfileResponse:
        """プロフィールを更新（UPSERT）"""
        now = datetime.now(timezone.utc).isoformat()
        pk = f"USER#{user.user_id}"
        sk = "PROFILE"

        try:
            existing = self.table.get_item(
                Key={"PK": pk, "SK": sk}).get("Item")
        except Exception:
            existing = None

        created_at = existing.get("createdAt", now) if existing else now

        self.table.put_item(Item={
            "PK": pk,
            "SK": sk,
            "postId": f"PROFILE#{user.user_id}",
            "userId": user.user_id,
            "nickname": body.nickname or (existing.get("nickname") if existing else None),
            "bio": body.bio or (existing.get("bio") if existing else None),
            "avatarKey": body.avatar_key or (existing.get("avatarKey") if existing else None),
            "createdAt": created_at,
            "updatedAt": now,
        })
        return self.get_profile(user.user_id)

    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        """画像アップロード用の署名付き URL を生成"""
        urls = []
        if not self.minio_client:
            # MinIO 未接続時はダミー URL
            for _ in range(count):
                key = f"images/{user.user_id}/{uuid.uuid4()}.jpg"
                urls.append({"url": f"http://localhost:8000/uploads/{key}", "key": key})
            return urls

        # boto3 で presigned URL を生成 (HTTP 接続なし・純粋なローカル計算)
        # minio:9000 (Docker 内部ホスト) で署名し /storage/ プロキシ経由の相対 URL に変換
        import boto3
        from botocore.config import Config
        s3_signing = boto3.client(
            "s3",
            endpoint_url="http://minio:9000",  # 内部ホストで署名
            aws_access_key_id=settings.minio_access_key or "minioadmin",
            aws_secret_access_key=settings.minio_secret_key or "minioadmin",
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )
        for _ in range(count):
            key = f"images/{user.user_id}/{uuid.uuid4()}.jpg"
            try:
                upload_url = s3_signing.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": settings.minio_bucket,
                        "Key": key,
                        "ContentType": "image/jpeg",
                    },
                    ExpiresIn=settings.presigned_url_expiry,
                )
            except Exception as exc:
                logger.error(f"Failed to generate presigned URL: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate upload URL",
                )
            # http://minio:9000 → /storage (相対 URL) に変換してブラウザから使用可能にする
            proxy_url = upload_url.replace("http://minio:9000", "/storage", 1)
            urls.append({"url": proxy_url, "key": key})
        return urls
