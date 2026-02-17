import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

from app.config import settings

logger = logging.getLogger(__name__)

serializer = TypeSerializer()
deserializer = TypeDeserializer()


def _serialize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {k: serializer.serialize(v) for k, v in item.items()}


def _deserialize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {k: deserializer.deserialize(v) for k, v in item.items()}


def dynamodb_table():
    if not settings.posts_table_name:
        raise RuntimeError("POSTS_TABLE_NAME is not set")
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.posts_table_name
    )


def s3_client():
    return boto3.client("s3", region_name=settings.aws_region)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode_next_token(key: dict[str, Any] | None) -> str | None:
    if not key:
        return None
    payload = json.dumps(key).encode("utf-8")
    return base64.b64encode(payload).decode("utf-8")


def decode_next_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        payload = base64.b64decode(token.encode("utf-8"))
        return json.loads(payload.decode("utf-8"))
    except Exception:
        logger.warning("Invalid nextToken provided")
        return None


def build_user_profile_key(user_id: str) -> dict[str, str]:
    return {"PK": f"USER#{user_id}", "SK": "PROFILE"}


def batch_get_profiles(user_ids: list[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    table = dynamodb_table()
    keys = [build_user_profile_key(uid) for uid in user_ids]
    request = {table.name: {"Keys": [_serialize_item(k) for k in keys]}}
    try:
        response = table.meta.client.batch_get_item(RequestItems=request)
    except ClientError:
        logger.exception("Failed to batch_get profiles")
        return {}
    items = response.get("Responses", {}).get(table.name, [])
    nickname_by_user_id: dict[str, str] = {}
    for item in items:
        data = _deserialize_item(item)
        nickname = data.get("nickname")
        user_id = data.get("userId")
        if isinstance(nickname, str) and nickname.strip() and isinstance(user_id, str):
            nickname_by_user_id[user_id] = nickname.strip()
    return nickname_by_user_id


def query_posts(limit: int, exclusive_start_key: dict[str, Any] | None):
    table = dynamodb_table()
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq("POSTS"),
        "ScanIndexForward": False,
        "Limit": limit,
    }
    if exclusive_start_key:
        kwargs["ExclusiveStartKey"] = exclusive_start_key
    return table.query(**kwargs)


def get_post_by_id(post_id: str) -> dict[str, Any] | None:
    table = dynamodb_table()
    res = table.query(
        IndexName="PostIdIndex",
        KeyConditionExpression=Key("postId").eq(post_id),
        Limit=1,
    )
    items = res.get("Items", [])
    return items[0] if items else None
