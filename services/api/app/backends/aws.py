"""AWS DynamoDB バックエンド"""
import uuid
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from app.backends import BaseBackend
from app.models import Message, MessageCreate

try:
    import boto3
    from boto3.dynamodb.conditions import Key
except ImportError:
    boto3 = None


def _decimals_to_floats(obj):
    """DynamoDB DecimalをPythonのfloat/intに変換"""
    if isinstance(obj, list):
        return [_decimals_to_floats(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _decimals_to_floats(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    else:
        return obj


class AWSBackend(BaseBackend):
    """AWS DynamoDB バックエンド"""

    def __init__(self, table_name: str, region: str):
        if not boto3:
            raise ImportError("boto3 is required for AWS backend")

        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)

    async def create_message(self, message: MessageCreate) -> Message:
        """メッセージを作成"""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()

        item = {
            "id": message_id,
            "content": message.content,
            "author": message.author,
            "created_at": now.isoformat(),
        }

        if message.image_url:
            item["image_url"] = message.image_url

        self.table.put_item(Item=item)

        return Message(
            id=message_id,
            content=message.content,
            author=message.author,
            image_url=message.image_url,
            created_at=now,
        )

    async def get_messages(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[List[Message], int]:
        """メッセージ一覧を取得"""
        # Scan all items (本番環境ではGSIを使うべき)
        response = self.table.scan()
        items = _decimals_to_floats(response.get("Items", []))

        # Sort by created_at
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        total = len(items)
        paginated_items = items[offset : offset + limit]

        messages = [
            Message(
                id=item["id"],
                content=item["content"],
                author=item["author"],
                image_url=item.get("image_url"),
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in paginated_items
        ]

        return messages, total

    async def get_message(self, message_id: str) -> Optional[Message]:
        """メッセージを1件取得"""
        response = self.table.get_item(Key={"id": message_id})
        item = response.get("Item")

        if not item:
            return None

        item = _decimals_to_floats(item)

        return Message(
            id=item["id"],
            content=item["content"],
            author=item["author"],
            image_url=item.get("image_url"),
            created_at=datetime.fromisoformat(item["created_at"]),
        )

    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除"""
        try:
            self.table.delete_item(Key={"id": message_id})
            return True
        except Exception:
            return False
