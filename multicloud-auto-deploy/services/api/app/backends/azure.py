"""Azure Cosmos DB バックエンド"""
import uuid
from datetime import datetime
from typing import List, Optional

from app.backends import BaseBackend
from app.models import Message, MessageCreate, MessageUpdate

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions
except ImportError:
    CosmosClient = None


class AzureBackend(BaseBackend):
    """Azure Cosmos DB バックエンド"""

    def __init__(
        self,
        endpoint: str,
        key: str,
        database_name: str = "simple-sns",
        container_name: str = "messages",
    ):
        if not CosmosClient:
            raise ImportError("azure-cosmos is required for Azure backend")

        self.client = CosmosClient(endpoint, key)
        self.database_name = database_name
        self.container_name = container_name
        
        # データベースとコンテナを取得（存在しない場合は作成）
        self._ensure_database_and_container()

    def _ensure_database_and_container(self):
        """データベースとコンテナの存在を確認し、なければ作成"""
        try:
            # データベースを取得または作成
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # コンテナを取得または作成（パーティションキーは id）
            # Serverlessモードの場合はoffer_throughputを指定しない
            self.container = self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/id"),
            )
            
            print(f"✅ Azure Cosmos DB container '{self.container_name}' ready")
        except exceptions.CosmosHttpResponseError as e:
            print(f"⚠️ Error setting up Cosmos DB: {e}")
            raise

    def _item_to_message(self, item: dict) -> Message:
        """Cosmos DBアイテムをMessageモデルに変換"""
        # Cosmos DBの内部フィールドを除外
        created_at = item.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        updated_at = item.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return Message(
            id=item["id"],
            content=item["content"],
            author=item["author"],
            image_url=item.get("image_url"),
            created_at=created_at,
            updated_at=updated_at,
        )

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

        # Cosmos DBにアイテムを作成
        self.container.create_item(body=item)

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
        # 全アイテムを取得（作成日時の降順）
        query = "SELECT * FROM c ORDER BY c.created_at DESC"
        
        try:
            items = list(self.container.query_items(
                query=query,
                enable_cross_partition_query=True,
            ))
            
            total = len(items)
            
            # ページネーション
            paginated_items = items[offset : offset + limit]
            
            messages = [self._item_to_message(item) for item in paginated_items]
            
            return messages, total
        except exceptions.CosmosHttpResponseError as e:
            print(f"⚠️ Error querying messages: {e}")
            return [], 0

    async def get_message(self, message_id: str) -> Optional[Message]:
        """メッセージを1件取得"""
        try:
            item = self.container.read_item(
                item=message_id,
                partition_key=message_id,
            )
            return self._item_to_message(item)
        except exceptions.CosmosResourceNotFoundError:
            return None
        except exceptions.CosmosHttpResponseError as e:
            print(f"⚠️ Error reading message {message_id}: {e}")
            return None

    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除"""
        try:
            self.container.delete_item(
                item=message_id,
                partition_key=message_id,
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
        except exceptions.CosmosHttpResponseError as e:
            print(f"⚠️ Error deleting message {message_id}: {e}")
            return False

    async def update_message(
        self, message_id: str, message: MessageUpdate
    ) -> Optional[Message]:
        """メッセージを更新"""
        try:
            # 既存のアイテムを取得
            existing_item = self.container.read_item(
                item=message_id,
                partition_key=message_id,
            )
        except exceptions.CosmosResourceNotFoundError:
            return None
        except exceptions.CosmosHttpResponseError as e:
            print(f"⚠️ Error reading message {message_id}: {e}")
            return None

        # 更新データを準備（None以外のフィールドのみ）
        update_data = message.model_dump(exclude_unset=True)
        if not update_data:
            # 何も更新するものがなければ既存のメッセージを返す
            return self._item_to_message(existing_item)

        # アイテムを更新
        for key, value in update_data.items():
            existing_item[key] = value
        
        existing_item["updated_at"] = datetime.utcnow().isoformat()

        # Cosmos DBを更新
        try:
            updated_item = self.container.replace_item(
                item=message_id,
                body=existing_item,
            )
            return self._item_to_message(updated_item)
        except exceptions.CosmosHttpResponseError as e:
            print(f"⚠️ Error updating message {message_id}: {e}")
            return None
