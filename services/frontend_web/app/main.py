import os
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings
from app.routers import auth, views

# Azure Functions / Lambda では CWD が保証されないため __file__ 基準で解決
_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# STAGE_NAME 環境変数でパスプレフィックスを決定
# 例: STAGE_NAME=sns → prefix="/sns"（CDN /sns/ 配信時に使用）
# ローカル開発では STAGE_NAME 未設定 → prefix="" のまま動作
_stage = Settings().stage_name
prefix = f"/{_stage}" if _stage else ""

# NOTE: root_path は設定しない。GCP/AWS/Azure のロードバランサーは
# /sns/* を Cloud Run/Lambda に転送する際にパスをストリップしないため、
# root_path を設定するとStarlette 0.50+ がパスを二重にストリップして404になる。
app = FastAPI(title="Simple SNS Web")


class COOPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Firebase Auth popup issues with COOP/COEP
        # To allow popup communication, we might need to relax these or set them carefully.
        # Setting "same-origin-allow-popups" allows the popup to communicate back.
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        return response


app.add_middleware(COOPMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

_static_path = f"{prefix}/static" if prefix else "/static"
app.mount(_static_path, StaticFiles(
    directory=os.path.join(_APP_DIR, "static")), name="static")

app.include_router(auth.router, prefix=prefix)


def _health() -> dict:
    return {"status": "ok"}


# NOTE: health エンドポイントは views.router より先に登録する。
# views.router 末尾の catch-all (/{path:path}) より優先させるため。
app.add_api_route(
    f"{prefix}/health" if prefix else "/health",
    _health,
    methods=["GET"],
    name="health",
)

app.include_router(views.router, prefix=prefix)
