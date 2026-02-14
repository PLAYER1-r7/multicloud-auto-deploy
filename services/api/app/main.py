"""FastAPI アプリケーション - Simple SNS API"""
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.models import HealthResponse

# ロギング設定
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(
    title="Simple SNS API",
    description="マルチクラウド対応のシンプルなSNS API (完全Python実装)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS設定
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip圧縮
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ルーター登録
from app.routes import messages, uploads

app.include_router(messages.router)
app.include_router(uploads.router)


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("🚀 Starting Simple SNS API v1.0.0")
    logger.info(f"☁️  Cloud Provider: {settings.cloud_provider.value}")
    logger.info(f"🔐 Auth Disabled: {settings.auth_disabled}")


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("👋 Shutting down Simple SNS API")


@app.get("/", response_model=HealthResponse)
async def root():
    """ルートエンドポイント - ヘルスチェック"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        cloud_provider=settings.cloud_provider.value,
        timestamp=datetime.utcnow(),
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """ヘルスチェックエンドポイント"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        cloud_provider=settings.cloud_provider.value,
        timestamp=datetime.utcnow(),
    )


# Lambda/Azure Functions/Cloud Functions用ハンドラー
# AWS Lambda
try:
    from mangum import Mangum

    handler = Mangum(app, lifespan="off")
except ImportError:
    pass
