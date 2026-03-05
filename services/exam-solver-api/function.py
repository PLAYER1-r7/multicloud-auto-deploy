"""Google Cloud Functions エントリーポイント"""
import asyncio
import functions_framework
from app.main import app as fastapi_app

# -------------------------------------------------------------------
# GCP Cloud Functions Gen 2 は Cloud Run 上で動作するため、
# 同一インスタンスが複数リクエストを処理する。
# イベントループをモジュールレベルで保持し、リクエスト毎の
# new_event_loop() 生成・破棄を廃止することで:
#   - メモリ断片化リスクを排除
#   - コールドスタート後の余分な割当オーバーヘッドを削減
#   - asyncio タスクのリークを防止
# -------------------------------------------------------------------
_loop: asyncio.AbstractEventLoop | None = None


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """モジュール共有イベントループを取得（クローズ済みなら再作成）"""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


@functions_framework.http
def handler(request):
    """Cloud Functions HTTP handler that forwards to FastAPI"""

    # Cloud Functions Request → ASGI scope 変換
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": "https",
        "path": request.path,
        "query_string": request.query_string if request.query_string else b"",
        "headers": [[k.lower().encode(), v.encode()] for k, v in request.headers.items()],
        "server": (request.host.split(":")[0], int(request.host.split(":")[1]) if ":" in request.host else 443),
    }

    # Request body
    body = request.get_data()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    # Response capture
    status_code = 200
    headers = []
    body_parts = []

    async def send(message):
        nonlocal status_code, headers, body_parts

        if message["type"] == "http.response.start":
            status_code = message["status"]
            headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))

    # FastAPI をモジュール共有ループで実行（インスタンス内再利用）
    loop = _get_event_loop()
    loop.run_until_complete(fastapi_app(scope, receive, send))

    # レスポンス構築
    response_body = b"".join(body_parts)
    response_headers = {
        k.decode(): v.decode()
        for k, v in headers
        if k.decode().lower() != "content-length"
    }

    return (response_body, status_code, response_headers)
