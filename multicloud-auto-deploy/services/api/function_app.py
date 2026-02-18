import azure.functions as func
import logging
from app.main import app as fastapi_app

# Azure Functions のエントリーポイント
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="HttpTrigger")
@app.route(route="{*route}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions HTTP trigger that forwards to FastAPI"""
    logging.info(f"Python HTTP trigger function processed a request. URL: {req.url}")
    logging.info(f"Route params: {req.route_params}")
    logging.info(f"Method: {req.method}")

    # CORS Preflight (OPTIONS) リクエストを直接処理
    if req.method == "OPTIONS":
        logging.info("Handling CORS preflight request")
        return func.HttpResponse(
            body="",
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Max-Age": "86400",
            },
        )

    # FastAPI ASGIアプリケーションをAzure Functionsで実行
    from fastapi import Request
    from starlette.responses import Response

    # Azure Functions Request → FastAPI Request 変換
    # route_params には "HttpTrigger/api/messages" のような値が入っている
    # または "HttpTrigger/messages"、"HttpTrigger/health" の場合もある
    route_path = req.route_params.get("route", "")

    # "HttpTrigger/" プレフィックスを削除
    if route_path.startswith("HttpTrigger/"):
        route_path = route_path[len("HttpTrigger/") :]
    elif route_path == "HttpTrigger":
        route_path = ""

    # FastAPIルーターのパス処理:
    # - "/", "/health", "/docs", "/redoc" などはそのまま
    # - "/messages/", "/uploads/" などは "/api/" プレフィックスを追加
    if route_path and not route_path.startswith("api/"):
        # ルートパスやヘルスチェック、ドキュメントはそのまま
        if route_path not in ["", "health", "docs", "redoc", "openapi.json"]:
            route_path = "api/" + route_path

    path = "/" + route_path if route_path else "/"

    logging.info(f"Converted path for FastAPI: {path}")

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
    try:
        await fastapi_app(scope, receive, send)
    except Exception as e:
        logging.error(f"Error in FastAPI application: {type(e).__name__}: {e}", exc_info=True)
        return func.HttpResponse(
            body=f'{{"error": "{type(e).__name__}", "message": "{str(e)}"}}',
            status_code=500,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # レスポンス構築
    response_body = b"".join(body_parts)
    response_headers = {k.decode(): v.decode() for k, v in headers}

    # CORSヘッダーを追加（FastAPIのミドルウェアからのヘッダーがない場合）
    if "Access-Control-Allow-Origin" not in response_headers:
        response_headers["Access-Control-Allow-Origin"] = "*"
        response_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response_headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With"
        )

    return func.HttpResponse(body=response_body, status_code=status_code, headers=response_headers)
