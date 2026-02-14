"""ローカル開発環境用バックエンド（インメモリストレージ）"""
import uuid
from datetime import datetime
from typing import List, Optional

from app.backends import BaseBackend
from app.models import Message, MessageCreate


class LocalBackend(BaseBackend):
    """ローカル開発用インメモリバックエンド"""

    def __init__(self):
        self._messages: dict[str, Message] = {}

    async def create_message(self, message: MessageCreate) -> Message:
        """メッセージを作成"""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()

        new_message = Message(
            id=message_id,
            content=message.content,
            author=message.author,
            image_url=message.image_url,
            created_at=now,
        )

        self._messages[message_id] = new_message
        return new_message

    async def get_messages(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[List[Message], int]:
        """メッセージ一覧を取得"""
        all_messages = sorted(
            self._messages.values(),
            key=lambda m: m.created_at,
            reverse=True,
        )

        total = len(all_messages)
        messages = all_messages[offset : offset + limit]

        return messages, total

    async def get_message(self, message_id: str) -> Optional[Message]:
        """メッセージを1件取得"""
        return self._messages.get(message_id)

    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除"""
        if message_id in self._messages:
            del self._messages[message_id]
            return True
        return False
