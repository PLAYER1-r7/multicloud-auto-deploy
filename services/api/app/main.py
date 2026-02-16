from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi import Query, Depends
import logging

from app.config import settings
from app.models import HealthResponse, ListPostsResponse, CreatePostBody
from app.routes import posts, profile, uploads
from app.backends import get_backend
from app.auth import UserInfo, require_user

# ロギング設定
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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
    user: UserInfo = Depends(require_user),
) -> dict:
    """旧フロントエンド互換: 投稿を作成 (POST /api/messages/)"""
    backend = get_backend()
    return backend.create_post(body, user)


@app.delete("/api/messages/{post_id}")
def legacy_delete_message(
    post_id: str,
    user: UserInfo = Depends(require_user),
) -> dict:
    """旧フロントエンド互換: 投稿を削除 (DELETE /api/messages/{id})"""
    backend = get_backend()
    return backend.delete_post(post_id, user)


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info(f"Starting Simple SNS API v3.0.0")
    logger.info(f"Cloud Provider: {settings.cloud_provider.value}")
    logger.info(f"Auth Disabled: {settings.auth_disabled}")


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("Shutting down Simple SNS API")


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    """ルートエンドポイント"""
    return HealthResponse(
        status="ok",
        provider=settings.cloud_provider.value,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """ヘルスチェックエンドポイント"""
    return HealthResponse(
        status="ok",
        provider=settings.cloud_provider.value,
    )


# AWS Lambda handler (Mangum)
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
    logger.info("Mangum handler initialized for AWS Lambda")
except ImportError:
    logger.warning("Mangum not available - AWS Lambda deployment not supported")
    handler = None
