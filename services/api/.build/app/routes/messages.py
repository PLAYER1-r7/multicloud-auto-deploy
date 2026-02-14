"""メッセージAPI ルーター"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.backends import BaseBackend
from app.backends.factory import get_backend
from app.models import Message, MessageCreate, MessageUpdate, MessageListResponse

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("/", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(
    message: MessageCreate,
    backend: Annotated[BaseBackend, Depends(get_backend)],
):
    """メッセージを作成"""
    return await backend.create_message(message)


@router.get("/", response_model=MessageListResponse)
async def get_messages(
    backend: Annotated[BaseBackend, Depends(get_backend)],
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
):
    """メッセージ一覧を取得"""
    offset = (page - 1) * page_size
    messages, total = await backend.get_messages(limit=page_size, offset=offset)

    return MessageListResponse(
        messages=messages,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{message_id}", response_model=Message)
async def get_message(
    message_id: str,
    backend: Annotated[BaseBackend, Depends(get_backend)],
):
    """メッセージを1件取得"""
    message = await backend.get_message(message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )

    return message


@router.put("/{message_id}", response_model=Message)
async def update_message(
    message_id: str,
    message: MessageUpdate,
    backend: Annotated[BaseBackend, Depends(get_backend)],
):
    """メッセージを更新"""
    updated_message = await backend.update_message(message_id, message)

    if not updated_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )

    return updated_message


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    backend: Annotated[BaseBackend, Depends(get_backend)],
):
    """メッセージを削除"""
    success = await backend.delete_message(message_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found",
        )

    return None
