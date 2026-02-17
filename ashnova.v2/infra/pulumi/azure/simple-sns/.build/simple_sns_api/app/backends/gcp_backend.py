import base64
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from google.cloud import firestore
from google.cloud import storage

from app import config
from app.auth import UserInfo
from app.models import CreatePostBody, Post, ProfileResponse, ProfileUpdateRequest, UploadUrlsRequest

logger = logging.getLogger(__name__)

_firestore_client: firestore.Client | None = None
_storage_client: storage.Client | None = None


def _get_firestore() -> firestore.Client:
    global _firestore_client
    if _firestore_client:
        return _firestore_client
    if not config.GCP_PROJECT_ID:
        raise HTTPException(
            status_code=500, detail="GCP project configuration missing")
    _firestore_client = firestore.Client(project=config.GCP_PROJECT_ID)
    return _firestore_client


def _get_storage() -> storage.Client:
    global _storage_client
    if _storage_client:
        return _storage_client
    if not config.GCP_PROJECT_ID:
        raise HTTPException(
            status_code=500, detail="GCP project configuration missing")
    _storage_client = storage.Client(project=config.GCP_PROJECT_ID)
    return _storage_client


def _encode_token(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    raw = json.dumps(payload).encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def _decode_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        raw = base64.b64decode(token.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("Invalid nextToken provided")
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_image_urls(keys: list[str]) -> list[str] | None:
    if not keys:
        return None
    if not config.GCP_STORAGE_BUCKET:
        raise HTTPException(status_code=500, detail="GCS bucket missing")
    storage_client = _get_storage()
    bucket = storage_client.bucket(config.GCP_STORAGE_BUCKET)
    urls = []
    for key in keys:
        blob = bucket.blob(key)
        try:
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=config.SIGNED_URL_EXPIRY),
                method="GET",
            )
            urls.append(url)
        except Exception:
            logger.exception("Failed to generate signed URL")
    return urls


class GcpBackend:
    def list_posts(self, limit: int, next_token: str | None, tag: str | None) -> tuple[list[Post], str | None]:
        db = _get_firestore()
        posts_ref = db.collection(config.GCP_POSTS_COLLECTION)
        query = posts_ref.order_by(
            "createdAt", direction=firestore.Query.DESCENDING)
        query = query.order_by(
            "postId", direction=firestore.Query.DESCENDING).limit(limit)

        cursor = _decode_token(next_token)
        if cursor and cursor.get("createdAt") and cursor.get("postId"):
            query = query.start_after(
                {"createdAt": cursor["createdAt"], "postId": cursor["postId"]})

        docs = list(query.stream())
        posts: list[Post] = []
        for doc in docs:
            data = doc.to_dict() or {}
            image_keys = data.get("imageKeys") or ([] if data.get(
                "imageKey") is None else [data.get("imageKey")])
            image_keys = [key for key in image_keys if isinstance(key, str)]
            post = Post(
                postId=data.get("postId"),
                userId=data.get("userId"),
                nickname=data.get("nickname"),
                content=data.get("content"),
                createdAt=data.get("createdAt"),
                isMarkdown=data.get("isMarkdown"),
                tags=data.get("tags"),
                imageUrls=_build_image_urls(image_keys),
            )
            posts.append(post)

        if tag:
            posts = [item for item in posts if item.tags and tag in item.tags]

        next_out = None
        if docs:
            last = docs[-1].to_dict() or {}
            next_out = _encode_token({"createdAt": last.get(
                "createdAt"), "postId": last.get("postId")})

        return posts, next_out

    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        db = _get_firestore()
        post_id = str(uuid.uuid4())
        created_at = _now_iso()

        profile_doc = db.collection(
            config.GCP_PROFILES_COLLECTION).document(user.user_id).get()
        profile = profile_doc.to_dict() if profile_doc.exists else None
        nickname = profile.get("nickname") if profile else None
        if not nickname:
            nickname = user.nickname

        item: dict[str, Any] = {
            "postId": post_id,
            "userId": user.user_id,
            "content": body.content,
            "createdAt": created_at,
            "docType": "post",
        }
        if body.imageKeys:
            item["imageKeys"] = body.imageKeys
        if body.isMarkdown:
            item["isMarkdown"] = True
        if body.tags:
            item["tags"] = body.tags
        if nickname:
            item["nickname"] = nickname

        db.collection(config.GCP_POSTS_COLLECTION).document(post_id).set(item)
        return {"item": item}

    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        db = _get_firestore()
        post_ref = db.collection(config.GCP_POSTS_COLLECTION).document(post_id)
        doc = post_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Post not found")
        data = doc.to_dict() or {}

        if not user.is_admin and data.get("userId") != user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        image_keys = data.get("imageKeys") or ([] if data.get(
            "imageKey") is None else [data.get("imageKey")])
        image_keys = [key for key in image_keys if isinstance(key, str)]

        if image_keys and config.GCP_STORAGE_BUCKET:
            storage_client = _get_storage()
            bucket = storage_client.bucket(config.GCP_STORAGE_BUCKET)
            for key in image_keys:
                try:
                    bucket.blob(key).delete()
                except Exception:
                    logger.exception("Failed to delete image",
                                     extra={"key": key})

        post_ref.delete()
        return {"message": "Post deleted", "postId": post_id}

    def get_profile(self, user: UserInfo) -> ProfileResponse:
        db = _get_firestore()
        doc = db.collection(config.GCP_PROFILES_COLLECTION).document(
            user.user_id).get()
        if not doc.exists:
            return ProfileResponse(userId=user.user_id, nickname="")
        data = doc.to_dict() or {}

        return ProfileResponse(
            userId=user.user_id,
            nickname=data.get("nickname") or "",
            updatedAt=data.get("updatedAt"),
            createdAt=data.get("createdAt"),
        )

    def update_profile(self, body: ProfileUpdateRequest, user: UserInfo) -> ProfileResponse:
        db = _get_firestore()
        now = _now_iso()
        profile_ref = db.collection(
            config.GCP_PROFILES_COLLECTION).document(user.user_id)
        existing = profile_ref.get()
        created_at = now
        if existing.exists:
            created_at = (existing.to_dict() or {}).get(
                "createdAt") or created_at

        item = {
            "userId": user.user_id,
            "nickname": body.nickname,
            "updatedAt": now,
            "createdAt": created_at,
            "docType": "profile",
        }
        profile_ref.set(item)

        return ProfileResponse(
            userId=user.user_id,
            nickname=body.nickname,
            updatedAt=now,
            createdAt=created_at,
        )

    def create_upload_urls(self, body: UploadUrlsRequest, user: UserInfo) -> dict:
        if not config.GCP_STORAGE_BUCKET:
            raise HTTPException(status_code=500, detail="GCS bucket missing")

        storage_client = _get_storage()
        bucket = storage_client.bucket(config.GCP_STORAGE_BUCKET)

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
            blob = bucket.blob(key)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=config.PRESIGNED_URL_EXPIRY),
                method="PUT",
                content_type=content_type,
            )
            urls.append({"url": url, "key": key, "contentType": content_type})

        return {
            "postId": post_id,
            "urls": urls,
            "expiresIn": config.PRESIGNED_URL_EXPIRY,
        }
