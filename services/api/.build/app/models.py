"""データモデル"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str = "ok"
    version: str = "1.0.0"
    cloud_provider: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MessageBase(BaseModel):
    """メッセージ基本モデル"""

    content: str = Field(..., min_length=1, max_length=1000)
    author: str = Field(..., min_length=1, max_length=100)
    image_url: Optional[str] = None


class MessageCreate(MessageBase):
    """メッセージ作成"""

    pass


class MessageUpdate(BaseModel):
    """メッセージ更新"""

    content: Optional[str] = Field(None, min_length=1, max_length=1000)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    image_url: Optional[str] = None


class Message(MessageBase):
    """メッセージ（レスポンス）"""

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    """メッセージリストレスポンス"""

    messages: list[Message]
    total: int
    page: int = 1
    page_size: int = 20
