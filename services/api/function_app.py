import azure.functions as func
import logging
from app.main import app as fastapi_app

# Azure Functions のエントリーポイント
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="HttpTrigger")
@app.route(route="{*route}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions HTTP trigger that forwards to FastAPI"""
    logging.info(f'Python HTTP trigger function processed a request. URL: {req.url}')
    logging.info(f'Route params: {req.route_params}')
    logging.info(f'Method: {req.method}')
    
    # FastAPI ASGIアプリケーションをAzure Functionsで実行
    from fastapi import Request
    from starlette.responses import Response
    
    # Azure Functions Request → FastAPI Request 変換
    # route_params には "HttpTrigger/health" のような値が入っているので、"HttpTrigger/" を削除
    route_path = req.route_params.get("route", "")
    if route_path.startswith("HttpTrigger/"):
        route_path = route_path[len("HttpTrigger/"):]
    elif route_path == "HttpTrigger":
        route_path = ""
    
    path = "/" + route_path if route_path else "/"
    
    logging.info(f'Converted path for FastAPI: {path}')
    
    # クエリ文字列を正しく抽出
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(req.url)
    query_string = parsed.query.encode("utf-8") if parsed.query else b""
    
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": req.method,
        "scheme": "https",
        "path": path,
        "query_string": query_string,
        "root_path": "",
        "headers": [[k.encode(), v.encode()] for k, v in req.headers.items()],
        "server": (parsed.hostname or "localhost", 443),
        "client": ("127.0.0.1", 0),
    }
    
    # FastAPI を ASGI で実行
    from io import BytesIO
    
    async def receive():
        return {"type": "http.request", "body": req.get_body()}
    
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
    
    # FastAPI アプリケーション実行
    await fastapi_app(scope, receive, send)
    
    # レスポンス構築
    response_body = b"".join(body_parts)
    response_headers = {k.decode(): v.decode() for k, v in headers}
    
    return func.HttpResponse(
        body=response_body,
        status_code=status_code,
        headers=response_headers
    )


