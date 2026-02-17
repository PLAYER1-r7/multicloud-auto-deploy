import logging
import secrets
import uuid
from typing import Any, Iterable

from fastapi import HTTPException

from app.config import settings
from app.auth import UserInfo
from app.aws_clients import (
    batch_get_profiles,
    decode_next_token,
    dynamodb_table,
    encode_next_token,
    get_post_by_id,
    now_iso,
    query_posts,
    s3_client,
)
from app.models import CreatePostBody, Post, ProfileResponse, ProfileUpdateRequest, UploadUrlsRequest

logger = logging.getLogger(__name__)


def _build_image_urls(image_keys: Iterable[str]) -> list[str] | None:
    keys = [key for key in image_keys if isinstance(key, str)]
    if not keys:
        return None

    if settings.images_cdn_url:
        return [f"{settings.images_cdn_url}/{key}" for key in keys]

    if not settings.images_bucket_name:
        return None
    # Public URL for caching and cost reduction
    return [
        f"https://{settings.images_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
        for key in keys
    ]


class AwsBackend:
    def list_posts(self, limit: int, next_token: str | None, tag: str | None) -> tuple[list[Post], str | None]:
        table = dynamodb_table()
        exclusive_start_key = decode_next_token(next_token)
        res = query_posts(limit, exclusive_start_key)

        items = res.get("Items", [])
        user_ids = sorted({item.get("userId")
                          for item in items if item.get("userId")})
        nickname_by_user_id = batch_get_profiles(
            [uid for uid in user_ids if isinstance(uid, str)])

        posts: list[Post] = []
        for item in items:
            post = Post(
                postId=item["postId"],
                userId=item["userId"],
                nickname=item.get("nickname"),
                content=item["content"],
                createdAt=item["createdAt"],
                isMarkdown=item.get("isMarkdown"),
                tags=item.get("tags"),
            )

            profile_nickname = nickname_by_user_id.get(post.userId)
            if profile_nickname:
                post.nickname = profile_nickname

            image_keys = item.get("imageKeys") or ([] if item.get(
                "imageKey") is None else [item.get("imageKey")])
            post.imageUrls = _build_image_urls(image_keys)

            posts.append(post)

        if tag:
            posts = [item for item in posts if item.tags and tag in item.tags]

        output_next_token = encode_next_token(res.get("LastEvaluatedKey"))
        return posts, output_next_token

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        if not settings.images_bucket_name:
            raise HTTPException(
                status_code=500, detail="IMAGES_BUCKET_NAME is not set")

        table = dynamodb_table()
        post_id = str(uuid.uuid4())
        created_at = now_iso()

        profile_key = {"PK": f"USER#{user.user_id}", "SK": "PROFILE"}
        profile = table.get_item(Key=profile_key).get("Item")
        profile_nickname = profile.get("nickname") if profile else None

        item: dict[str, Any] = {
            "PK": "POSTS",
            "SK": f"{created_at}#{post_id}",
            "postId": post_id,
            "userId": user.user_id,
            "content": body.content,
            "createdAt": created_at,
        }

        if body.imageKeys:
            item["imageKeys"] = body.imageKeys
        if body.isMarkdown:
            item["isMarkdown"] = True
        if body.tags:
            item["tags"] = body.tags

        nickname = profile_nickname or user.nickname
        if nickname:
            item["nickname"] = nickname

        table.put_item(Item=item)
        return {"item": item}

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        try:
            uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid postId")

        table = dynamodb_table()
        post = get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if not user.is_admin and post.get("userId") != user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        image_keys = post.get("imageKeys") or ([] if post.get(
            "imageKey") is None else [post.get("imageKey")])
        image_keys = [k for k in image_keys if isinstance(k, str)]

        if image_keys:
            s3 = s3_client()
            for key in image_keys:
                try:
                    if settings.images_bucket_name:
                        s3.delete_object(
                            Bucket=settings.images_bucket_name, Key=key)
                except Exception:
                    logger.exception("Failed to delete image",
                                     extra={"key": key})

        table.delete_item(Key={"PK": post["PK"], "SK": post["SK"]})
        return {"message": "Post deleted", "postId": post_id}

    def get_profile(self, user: UserInfo) -> ProfileResponse:
        table = dynamodb_table()
        key = {"PK": f"USER#{user.user_id}", "SK": "PROFILE"}
        item = table.get_item(Key=key).get("Item")
        if not item:
            return ProfileResponse(userId=user.user_id, nickname="")

        return ProfileResponse(
            userId=user.user_id,
            nickname=item.get("nickname") or "",
            updatedAt=item.get("updatedAt"),
            createdAt=item.get("createdAt"),
        )

    def update_profile(self, body: ProfileUpdateRequest, user: UserInfo) -> ProfileResponse:
        table = dynamodb_table()
        key = {"PK": f"USER#{user.user_id}", "SK": "PROFILE"}
        now = now_iso()
        existing = table.get_item(Key=key).get("Item")
        created_at = existing.get("createdAt") if existing else now

        item = {
            **key,
            "userId": user.user_id,
            "nickname": body.nickname,
            "updatedAt": now,
            "createdAt": created_at,
            "docType": "profile",
        }
        table.put_item(Item=item)

        return ProfileResponse(
            userId=user.user_id,
            nickname=body.nickname,
            updatedAt=now,
            createdAt=created_at,
        )

    def create_upload_urls(self, body: UploadUrlsRequest, user: UserInfo) -> dict:
        if not settings.images_bucket_name:
            raise HTTPException(
                status_code=500, detail="IMAGES_BUCKET_NAME is not set")

        s3 = s3_client()
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
            url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.images_bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                    "Metadata": {
                        "uploaded-by": user.user_id,
                        "post-id": post_id,
                        "image-index": str(index),
                    },
                },
                ExpiresIn=settings.presigned_url_expiry,
            )
            urls.append({"url": url, "key": key})

        return {
            "postId": post_id,
            "urls": urls,
            "expiresIn": settings.presigned_url_expiry,
        }
