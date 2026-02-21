import logging
import os
import sys
import traceback
from urllib.parse import urlparse

import azure.functions as func

logger = logging.getLogger(__name__)

# Attempt to import FastAPI app — capture any error for diagnostics
_IMPORT_ERROR: str | None = None
fastapi_app = None
try:
    from app.main import app as fastapi_app
    logger.info("frontend_web: FastAPI app imported successfully")
except Exception as _e:
    _IMPORT_ERROR = traceback.format_exc()
    logger.error(
        f"frontend_web: Failed to import FastAPI app: {_e}\n{_IMPORT_ERROR}")

# Azure Functions v2 programmatic model
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="Web")
@app.route(route="{*path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Forward all requests to the FastAPI SSR app"""
    logger.info(f"HTTP trigger: {req.method} {req.url}")

    # Return diagnostic info if FastAPI app failed to import
    if fastapi_app is None:
        return func.HttpResponse(
            body=f"<h1>Import Error</h1><pre>{_IMPORT_ERROR}</pre>",
            status_code=503,
            headers={"Content-Type": "text/html"},
        )

    # CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            body="",
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Cookie",
                "Access-Control-Max-Age": "86400",
            },
        )

    route_path = req.route_params.get("path", "")
    path = "/" + route_path if route_path else "/"

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

    async def receive():
        return {"type": "http.request", "body": req.get_body()}

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

    try:
        await fastapi_app(scope, receive, send)
    except Exception as e:
        logger.error(f"FastAPI error: {type(e).__name__}: {e}", exc_info=True)
        return func.HttpResponse(
            body=f"<h1>Internal Server Error</h1><pre>{type(e).__name__}: {e}</pre>",
            status_code=500,
            headers={"Content-Type": "text/html"},
        )

    response_body = b"".join(body_parts)

    # Build headers dict — exclude set-cookie (multiple values must be added individually)
    response_headers = {}
    set_cookie_values = []
    for k, v in headers:
        key = k.decode()
        val = v.decode()
        if key.lower() == "set-cookie":
            set_cookie_values.append(val)
        else:
            response_headers[key] = val

    http_response = func.HttpResponse(
        body=response_body,
        status_code=status_code,
        headers=response_headers,
    )
    # Add each set-cookie header individually (HttpResponseHeaders.add supports multi-value)
    for cookie_val in set_cookie_values:
        http_response.headers.add("set-cookie", cookie_val)

    return http_response
