import azure.functions as func
import logging
from app.main import app as fastapi_app

# Azure Functions のエントリーポイント
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="HttpTrigger")
@app.route(route="{*route}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions HTTP trigger that forwards to FastAPI"""
    import json
    
    logging.info(f'Python HTTP trigger function processed a request. URL: {req.url}')
    logging.info(f'Route params: {req.route_params}')
    logging.info(f'Method: {req.method}')
    
    # DEBUG: 直接レスポンスを返して動作確認
    debug_info = {
        "url": req.url,
        "method": req.method,
        "route_params": dict(req.route_params),
        "headers": dict(req.headers)
    }
    logging.info(f'DEBUG INFO: {json.dumps(debug_info)}')
    
    return func.HttpResponse(
        body=json.dumps({"status": "debug", "info": debug_info}, indent=2),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )

