"""Google Cloud Functions エントリーポイント"""
import functions_framework
from app.main import app as fastapi_app

@functions_framework.http
def handler(request):
    """Cloud Functions HTTP handler that forwards to FastAPI"""
    import asyncio
    from io import BytesIO
    
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
    response_started = False
    status_code = 200
    headers = []
    body_parts = []
    
    async def send(message):
        nonlocal response_started, status_code, headers, body_parts
        
        if message["type"] == "http.response.start":
            response_started = True
            status_code = message["status"]
            headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))
    
    # FastAPI を同期的に実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(fastapi_app(scope, receive, send))
    finally:
        loop.close()
    
    # レスポンス構築
    response_body = b"".join(body_parts)
    response_headers = {k.decode(): v.decode() for k, v in headers if k.decode().lower() != "content-length"}
    
    return (response_body, status_code, response_headers)
