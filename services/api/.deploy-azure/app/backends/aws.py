"""AWS DynamoDB バックエンド"""
import uuid
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from app.backends import BaseBackend
from app.models import Message, MessageCreate, MessageUpdate

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

    def __init__(self, table_name: str, region: str = None):
        if not boto3:
            raise ImportError("boto3 is required for AWS backend")

        # If region is not provided, boto3 will use default region from environment
        if region:
            self.dynamodb = boto3.resource("dynamodb", region_name=region)
        else:
            self.dynamodb = boto3.resource("dynamodb")
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

    async def update_message(
        self, message_id: str, message: MessageUpdate
    ) -> Optional[Message]:
        """メッセージを更新"""
        # 既存のメッセージを取得
        existing_message = await self.get_message(message_id)
        if not existing_message:
            return None

        # 更新データを準備（None以外のフィールドのみ）
        update_data = message.model_dump(exclude_unset=True)
        if not update_data:
            # 何も更新するものがなければ既存のメッセージを返す
            return existing_message

        # DynamoDB用の更新式を構築
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        for idx, (key, value) in enumerate(update_data.items()):
            if idx > 0:
                update_expression += ", "
            # DynamoDBの予約語を避けるため属性名にプレースホルダを使用
            attr_name = f"#{key}"
            attr_value = f":val{idx}"
            update_expression += f"{attr_name} = {attr_value}"
            expression_attribute_names[attr_name] = key
            expression_attribute_values[attr_value] = value
        
        # updated_atを追加
        now = datetime.utcnow()
        update_expression += ", #updated_at = :updated_at"
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = now.isoformat()

        # DynamoDBを更新
        try:
            response = self.table.update_item(
                Key={"id": message_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW",
            )
            
            item = _decimals_to_floats(response.get("Attributes", {}))
            
            return Message(
                id=item["id"],
                content=item["content"],
                author=item["author"],
                image_url=item.get("image_url"),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
            )
        except Exception as e:
            print(f"⚠️ Error updating message {message_id}: {e}")
            return None

