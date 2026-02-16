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
        logger.info(f"Initialized AwsBackend with table={self.table_name}, bucket={self.bucket_name}")
    
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
                posts.append(
                    Post(
                        postId=item["postId"],
                        userId=item["userId"],
                        content=item["content"],
                        tags=item.get("tags", []),
                        createdAt=item["createdAt"],
                        updatedAt=item.get("updatedAt"),
                        imageUrls=item.get("imageUrls", []),
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
            
            item = {
                "PK": "POSTS",
                "SK": now + "#" + post_id,  # タイムスタンプ + UUID
                "postId": post_id,
                "userId": user.user_id,
                "content": body.content,
                "tags": body.tags if body.tags else [],
                "createdAt": now,
                "updatedAt": now,
                "imageUrls": body.image_keys if body.image_keys else [],
            }
            
            self.table.put_item(Item=item)
            
            return {
                "post_id": post_id,
                "user_id": user.user_id,
                "content": body.content,
                "tags": item["tags"],
                "created_at": now,
               "image_urls": item["imageUrls"],
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
                raise PermissionError("You do not have permission to delete this post")
            
            # 削除
            self.table.delete_item(Key={"PK": "POSTS", "SK": item["SK"]})
            
            return {"status": "deleted", "post_id": post_id}
            
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            raise
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        """プロフィールを取得"""
        # プロフィール機能は未実装
        return ProfileResponse(
            user_id=user_id,
            display_name=user_id,
            bio="",
            avatar_url="",
        )
    
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """プロフィールを更新"""
        # プロフィール機能は未実装
        return ProfileResponse(
            user_id=user.user_id,
            display_name=body.display_name or user.user_id,
            bio=body.bio or "",
            avatar_url=body.avatar_url or "",
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
            
            # 公開URLも作成
            public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
            
            urls.append(
                {
                    "upload_url": presigned_url,
                    "public_url": public_url,
                    "image_id": image_id,
                }
            )
        
        return urls
