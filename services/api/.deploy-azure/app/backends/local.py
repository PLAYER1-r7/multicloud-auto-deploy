"""ローカル開発環境用バックエンド（MinIO ストレージ）"""
import json
import uuid
from datetime import datetime
from typing import List, Optional
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.backends import BaseBackend
from app.models import Message, MessageCreate
from app.config import settings


class LocalBackend(BaseBackend):
    """ローカル開発用 MinIO バックエンド"""

    def __init__(self):
        # MinIO クライアントの初期化
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,  # HTTP (非SSL)
        )
        self.bucket_name = settings.minio_bucket_name
        
        # バケットが存在しない場合は作成
        self._ensure_bucket()

    def _ensure_bucket(self):
        """バケットの存在を確認し、なければ作成"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✅ MinIO bucket '{self.bucket_name}' created")
        except S3Error as e:
            print(f"⚠️ Error checking/creating bucket: {e}")

    def _get_object_key(self, message_id: str) -> str:
        """メッセージIDからオブジェクトキーを生成"""
        return f"messages/{message_id}.json"

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

        # MinIO に JSON として保存
        object_key = self._get_object_key(message_id)
        data = json.dumps(new_message.model_dump(mode='json'), ensure_ascii=False).encode('utf-8')
        
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_key,
            data=BytesIO(data),
            length=len(data),
            content_type="application/json",
        )

        return new_message

    async def get_messages(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[List[Message], int]:
        """メッセージ一覧を取得"""
        messages = []
        
        try:
            # messages/ プレフィックスのオブジェクトを一覧取得
            objects = self.client.list_objects(
                self.bucket_name,
                prefix="messages/",
                recursive=True,
            )
            
            for obj in objects:
                try:
                    # オブジェクトの内容を取得
                    response = self.client.get_object(self.bucket_name, obj.object_name)
                    data = json.loads(response.read().decode('utf-8'))
                    
                    # datetime 文字列を datetime オブジェクトに変換
                    if isinstance(data.get('created_at'), str):
                        data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                    if data.get('updated_at') and isinstance(data['updated_at'], str):
                        data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
                    
                    messages.append(Message(**data))
                    response.close()
                    response.release_conn()
                except Exception as e:
                    print(f"⚠️ Error reading message {obj.object_name}: {e}")
                    continue
            
            # 作成日時の降順でソート
            messages.sort(key=lambda m: m.created_at, reverse=True)
            
            total = len(messages)
            paginated_messages = messages[offset : offset + limit]
            
            return paginated_messages, total
            
        except S3Error as e:
            print(f"⚠️ Error listing messages: {e}")
            return [], 0

    async def get_message(self, message_id: str) -> Optional[Message]:
        """メッセージを1件取得"""
        object_key = self._get_object_key(message_id)
        
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            data = json.loads(response.read().decode('utf-8'))
            response.close()
            response.release_conn()
            
            # datetime 文字列を datetime オブジェクトに変換
            if isinstance(data.get('created_at'), str):
                data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            if data.get('updated_at') and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            
            return Message(**data)
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            print(f"⚠️ Error getting message {message_id}: {e}")
            return None

    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除"""
        object_key = self._get_object_key(message_id)
        
        try:
            self.client.remove_object(self.bucket_name, object_key)
            return True
        except S3Error as e:
            print(f"⚠️ Error deleting message {message_id}: {e}")
            return False

    async def update_message(
        self, message_id: str, message: "MessageUpdate"
    ) -> Optional[Message]:
        """メッセージを更新"""
        # 既存のメッセージを取得
        existing_message = await self.get_message(message_id)
        if not existing_message:
            return None
        
        # 更新データをマージ（None以外のフィールドのみ更新）
        update_data = message.model_dump(exclude_unset=True)
        updated_message_data = existing_message.model_dump()
        updated_message_data.update(update_data)
        updated_message_data["updated_at"] = datetime.utcnow()
        
        # MinIOに保存
        updated_message = Message(**updated_message_data)
        object_key = self._get_object_key(message_id)
        
        try:
            data = json.dumps(
                updated_message.model_dump(mode='json'), ensure_ascii=False
            ).encode('utf-8')
            
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=BytesIO(data),
                length=len(data),
                content_type="application/json",
            )
            
            return updated_message
        except S3Error as e:
            print(f"⚠️ Error updating message {message_id}: {e}")
            return None

