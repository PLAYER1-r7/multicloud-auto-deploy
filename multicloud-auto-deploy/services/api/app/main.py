"""
Multi-cloud Simple SNS API (v1.2.4)
CORS-hardened version for production deployment - AWS Lambda Layer permissions fix
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi import Query, Depends
from typing import Optional
import logging

from app.config import settings
from app.models import HealthResponse, ListPostsResponse, CreatePostBody
from app.routes import posts, profile, uploads
from app.backends import get_backend
from app.auth import UserInfo, require_user, get_current_user

# AWS Lambda Powertools (observability)
try:
    from aws_lambda_powertools import Logger, Tracer, Metrics
    from aws_lambda_powertools.metrics import MetricUnit

    # Powertools Logger (構造化ログ)
    logger = Logger(service="simple-sns-api")
    tracer = Tracer(service="simple-sns-api")
    metrics = Metrics(namespace="SimpleSNS", service="api")

    powertools_available = True
except ImportError:
    # Powertools が利用できない場合は標準loggingを使用
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    powertools_available = False

# FastAPIアプリケーション
app = FastAPI(
    title="Simple SNS API",
    description="マルチクラウド対応のシンプルなSNS API",
    version="3.0.0",
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
app.include_router(posts.router)
app.include_router(uploads.router)
app.include_router(profile.router)


# ========================================
# 後方互換性: 旧フロントエンド用の /api/messages エイリアス
# ========================================
@app.get("/api/messages/", response_model=ListPostsResponse)
def legacy_list_messages(
    limit: int = Query(20, ge=1, le=50, alias="page_size", description="取得件数"),
    nextToken: str | None = Query(None, description="ページネーショントークン"),
    tag: str | None = Query(None, description="タグフィルター"),
) -> ListPostsResponse:
    """旧フロントエンド互換: 投稿一覧を取得 (GET /api/messages/)"""
    backend = get_backend()
    posts_list, output_next_token = backend.list_posts(limit, nextToken, tag)
    return ListPostsResponse(items=posts_list, limit=limit, nextToken=output_next_token)


@app.post("/api/messages/", status_code=201)
def legacy_create_message(
    body: CreatePostBody,
    user: Optional[UserInfo] = Depends(get_current_user),
) -> dict:
    """旧フロントエンド互換: 投稿を作成 (POST /api/messages/)"""
    # staging環境では認証をオプショナルに（匿名ユーザーを使用）
    if not user:
        user = UserInfo(
            user_id="anonymous",
            email="anonymous@example.com",
            groups=None,
        )
    backend = get_backend()
    return backend.create_post(body, user)


@app.delete("/api/messages/{post_id}")
def legacy_delete_message(
    post_id: str,
    user: Optional[UserInfo] = Depends(get_current_user),
) -> dict:
    """旧フロントエンド互換: 投稿を削除 (DELETE /api/messages/{id})"""
    # staging環境では認証をオプショナルに
    if not user:
        user = UserInfo(
            user_id="anonymous",
            email="anonymous@example.com",
            groups=None,
        )
    backend = get_backend()
    return backend.delete_post(post_id, user)


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info(
        "Starting Simple SNS API",
        extra={
            "version": "3.0.0",
            "cloud_provider": settings.cloud_provider.value,
            "auth_disabled": settings.auth_disabled,
            "powertools_enabled": powertools_available,
        },
    )


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("Shutting down Simple SNS API")


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    """ルートエンドポイント"""
    if powertools_available:
        metrics.add_metric(name="RootEndpointCalled", unit=MetricUnit.Count, value=1)

    return HealthResponse(
        status="ok",
        provider=settings.cloud_provider.value,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """ヘルスチェックエンドポイント"""
    if powertools_available:
        metrics.add_metric(name="HealthCheckCalled", unit=MetricUnit.Count, value=1)

    logger.info("Health check requested", extra={"provider": settings.cloud_provider.value})

    return HealthResponse(
        status="ok",
        provider=settings.cloud_provider.value,
    )


# AWS Lambda handler (Mangum)
try:
    from mangum import Mangum

    _mangum_handler = Mangum(app, lifespan="off")

    if powertools_available:
        # Powertools decorators を Lambda handler に適用
        @logger.inject_lambda_context(clear_state=True)
        @tracer.capture_lambda_handler
        @metrics.log_metrics(capture_cold_start_metric=True)
        def handler(event, context):
            return _mangum_handler(event, context)

        logger.info("Mangum handler initialized with Powertools support")
    else:
        handler = _mangum_handler
        logger.info("Mangum handler initialized for AWS Lambda")

except ImportError:
    logger.warning("Mangum not available - AWS Lambda deployment not supported")
    handler = None
