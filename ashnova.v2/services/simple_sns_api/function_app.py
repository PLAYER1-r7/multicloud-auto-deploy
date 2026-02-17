import azure.functions as func

from app.main import app as fastapi_app

app = func.FunctionApp()


@app.function_name(name="Api")
@app.route(route="{*path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def main(req: func.HttpRequest, context: func.Context):
    return func.AsgiMiddleware(fastapi_app).handle(req, context)
