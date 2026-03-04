"""GCP Cloud Functions - Simplified wrapper"""
import asyncio
from typing import Any
import functions_framework
from app.main import app as fastapi_app


@functions_framework.http
def handler(request):
    """Handle HTTP requests in Cloud Functions Gen 2"""
    
    # Convert Flask/Werkzeug request to ASGI scope
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": request.scheme or "https",
        "path": request.path or "/",
        "query_string": request.query_string or b"",
        "root_path": "",
        "headers": [[k.lower().encode(), v.encode()] for k, v in request.headers.items()],
        "server": (request.host.split(":")[0] if request.host else "localhost", 8080),
        "client": (request.remote_addr or "127.0.0.1", 0),
    }
    
    # Get request body
    body = request.get_data()
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    # Capture response
    response_started = False
    status_code = 200
    response_headers = []
    body_parts = []
    
    async def send(message: dict[str, Any]) -> None:
        nonlocal response_started, status_code, response_headers
        
        if message["type"] == "http.response.start":
            response_started = True
            status_code = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))
    
    # Run FastAPI app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(fastapi_app(scope, receive, send))
    finally:
        loop.close()
    
    # Build response
    from werkzeug.wrappers import Response
    response_body = b"".join(body_parts)
    response_headers_dict = {
        k.decode(): v.decode()
        for k, v in response_headers
        if k.decode().lower() != "content-length"
    }
    
    return Response(response_body, status=status_code, headers=response_headers_dict)
