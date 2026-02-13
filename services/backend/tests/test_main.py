import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_root():
    """ルートエンドポイントのテスト"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "cloud" in data
    assert "status" in data

def test_health_check():
    """ヘルスチェックのテスト"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "cloud" in data
    assert "timestamp" in data

def test_create_message():
    """メッセージ作成のテスト"""
    message_data = {"text": "Test message"}
    response = client.post("/api/messages", json=message_data)
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Test message"
    assert "id" in data
    assert "timestamp" in data
    assert "cloud" in data

def test_get_messages():
    """メッセージ一覧取得のテスト"""
    response = client.get("/api/messages")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_message_not_found():
    """存在しないメッセージの取得テスト"""
    response = client.get("/api/messages/nonexistent-id")
    assert response.status_code == 404

def test_delete_message():
    """メッセージ削除のテスト"""
    # まずメッセージを作成
    message_data = {"text": "Message to delete"}
    create_response = client.post("/api/messages", json=message_data)
    message_id = create_response.json()["id"]
    
    # 削除
    delete_response = client.delete(f"/api/messages/{message_id}")
    assert delete_response.status_code == 200
    
    # 削除されたことを確認
    get_response = client.get(f"/api/messages/{message_id}")
    assert get_response.status_code == 404
