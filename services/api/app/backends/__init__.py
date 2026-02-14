"""データベースバックエンドの抽象基底クラス"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app.models import Message, MessageCreate


class BaseBackend(ABC):
    """データベースバックエンドの抽象基底クラス"""

    @abstractmethod
    async def create_message(self, message: MessageCreate) -> Message:
        """メッセージを作成"""
        pass

    @abstractmethod
    async def get_messages(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[List[Message], int]:
        """メッセージ一覧を取得 (messages, total_count)"""
        pass

    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[Message]:
        """メッセージを1件取得"""
        pass

    @abstractmethod
    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除"""
        pass
