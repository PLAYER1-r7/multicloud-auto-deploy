"""GCP Firestore バックエンド"""
import uuid
from datetime import datetime
from typing import List, Optional

from app.backends import BaseBackend
from app.models import Message, MessageCreate, MessageUpdate

try:
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_query import FieldFilter
except ImportError:
    firestore = None


class GCPBackend(BaseBackend):
    """GCP Firestore バックエンド"""

    def __init__(self, project_id: str, collection_name: str = "messages"):
        if not firestore:
            raise ImportError("google-cloud-firestore is required for GCP backend")

        self.db = firestore.Client(project=project_id)
        self.collection_name = collection_name

    def _doc_to_message(self, doc) -> Message:
        """FirestoreドキュメントをMessageモデルに変換"""
        data = doc.to_dict()
        
        # Firestore TimestampをPython datetimeに変換
        created_at = data.get("created_at")
        if hasattr(created_at, "timestamp"):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        updated_at = data.get("updated_at")
        if updated_at:
            if hasattr(updated_at, "timestamp"):
                updated_at = datetime.fromtimestamp(updated_at.timestamp())
            elif isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return Message(
            id=doc.id,
            content=data["content"],
            author=data["author"],
            image_url=data.get("image_url"),
            created_at=created_at,
            updated_at=updated_at,
        )

    async def create_message(self, message: MessageCreate) -> Message:
        """メッセージを作成"""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()

        doc_data = {
            "content": message.content,
            "author": message.author,
            "created_at": now,
        }

        if message.image_url:
            doc_data["image_url"] = message.image_url

        # Firestoreにドキュメントを作成
        doc_ref = self.db.collection(self.collection_name).document(message_id)
        doc_ref.set(doc_data)

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
        # 全ドキュメントを取得してカウント
        all_docs = (
            self.db.collection(self.collection_name)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        
        all_messages = [self._doc_to_message(doc) for doc in all_docs]
        total = len(all_messages)
        
        # ページネーション
        paginated_messages = all_messages[offset : offset + limit]
        
        return paginated_messages, total

    async def get_message(self, message_id: str) -> Optional[Message]:
        """メッセージを1件取得"""
        doc_ref = self.db.collection(self.collection_name).document(message_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return self._doc_to_message(doc)

    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(message_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"⚠️ Error deleting message {message_id}: {e}")
            return False

    async def update_message(
        self, message_id: str, message: MessageUpdate
    ) -> Optional[Message]:
        """メッセージを更新"""
        doc_ref = self.db.collection(self.collection_name).document(message_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        # 更新データを準備（None以外のフィールドのみ）
        update_data = message.model_dump(exclude_unset=True)
        if not update_data:
            # 何も更新するものがなければ既存のメッセージを返す
            return self._doc_to_message(doc)

        # updated_atを追加
        update_data["updated_at"] = datetime.utcnow()

        # Firestoreを更新
        try:
            doc_ref.update(update_data)
            
            # 更新後のドキュメントを取得
            updated_doc = doc_ref.get()
            return self._doc_to_message(updated_doc)
        except Exception as e:
            print(f"⚠️ Error updating message {message_id}: {e}")
            return None
