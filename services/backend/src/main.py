from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime
import json

# クラウドプロバイダーの検出
def detect_cloud_provider():
    """実行環境からクラウドプロバイダーを検出"""
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return 'AWS'
    elif os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT'):
        return 'Azure'
    elif os.environ.get('K_SERVICE'):  # Cloud Run
        return 'GCP'
    elif os.environ.get('FUNCTION_NAME'):  # Cloud Functions
        return 'GCP'
    return 'Local'

# アプリケーション初期化
app = FastAPI(
    title="Multi-Cloud Auto Deploy API",
    description="マルチクラウド対応のバックエンドAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なオリジンを設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データモデル
class Message(BaseModel):
    id: Optional[str] = None
    text: str
    timestamp: Optional[str] = None
    cloud: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    cloud: str
    timestamp: str

# インメモリストレージ（本番環境ではDBを使用）
messages_store: List[Message] = []

# クラウドプロバイダー
CLOUD_PROVIDER = detect_cloud_provider()

@app.get("/")
def read_root():
    """ルートエンドポイント"""
    return {
        "message": "Multi-Cloud Auto Deploy API",
        "cloud": CLOUD_PROVIDER,
        "status": "running"
    }

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """ヘルスチェック"""
    return HealthResponse(
        status="healthy",
        cloud=CLOUD_PROVIDER,
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/messages", response_model=List[Message])
def get_messages():
    """全メッセージを取得"""
    return messages_store

@app.post("/api/messages", response_model=Message)
def create_message(message: Message):
    """新規メッセージを作成"""
    message.id = str(uuid.uuid4())
    message.timestamp = datetime.utcnow().isoformat()
    message.cloud = CLOUD_PROVIDER
    messages_store.append(message)
    return message

@app.get("/api/messages/{message_id}", response_model=Message)
def get_message(message_id: str):
    """特定のメッセージを取得"""
    for msg in messages_store:
        if msg.id == message_id:
            return msg
    raise HTTPException(status_code=404, detail="Message not found")

@app.delete("/api/messages/{message_id}")
def delete_message(message_id: str):
    """メッセージを削除"""
    global messages_store
    original_length = len(messages_store)
    messages_store = [msg for msg in messages_store if msg.id != message_id]
    
    if len(messages_store) == original_length:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Message deleted successfully"}

# AWS Lambda用ハンドラー（Mangum使用）
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    pass

# Azure Functions用エントリポイント
def main(req):
    """Azure Functions用のメインハンドラー"""
    # Azure Functions統合は別途実装
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
