"""Google Cloud Functions HTTP handler"""
import functions_framework
from app.main import app


@functions_framework.http
def handler(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        (https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.make_response).
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        return ("", 204, headers)

    # Create ASGI scope from Flask request
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": "https",
        "path": request.path,
        "query_string": request.query_string or b"",
        "root_path": "",
        "headers": [
            [k.lower().encode(), v.encode()] 
            for k, v in request.headers 
            if k.lower() not in ("content-length",)
        ],
        "server": ("localhost", 8080),
        "client": ("127.0.0.1", 0),
    }

    # Prepare request body
    body = request.get_data()

    # Track response
    status = 200
    response_headers = []
    response_body = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        nonlocal status, response_headers
        if message["type"] == "http.response.start":
            status = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    # Run async ASGI app
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(app(scope, receive, send))
    finally:
        loop.close()

    # Prepare Flask response
    headers = {
        k.decode(): v.decode()
        for k, v in response_headers
        if k.decode().lower() != "content-length"
    }
    
    return (b"".join(response_body), status, headers)
