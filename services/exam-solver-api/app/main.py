import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import HealthResponse
from app.routes import solve

try:
    from app.routes import learning
except ImportError:
    learning = None

# AWS Lambda Powertools (observability)
try:
    from aws_lambda_powertools import Logger, Metrics, Tracer
    from aws_lambda_powertools.metrics import MetricUnit

    logger = Logger(service="exam-solver-api")
    tracer = Tracer(service="exam-solver-api")
    metrics = Metrics(namespace="ExamSolver", service="api")

    powertools_available = True
except ImportError:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    powertools_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    logger.info(
        "Starting Exam Solver API",
        extra={
            "version": "1.0.0",
            "cloud_provider": settings.cloud_provider.value,
        },
    )
    yield
    logger.info("Shutting down Exam Solver API")


# FastAPI アプリケーション
app = FastAPI(
    title="Exam Solver API",
    description="大学入試解答サッポートサービス（OCR・AI解答）",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS 設定
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip 圧縮
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Cache Control Middleware ───────────────────────────────────────────────
async def add_cache_control_headers(request: Request, call_next):
    """Add Cache-Control headers based on file type and path."""
    response = await call_next(request)
    path = request.url.path.lower()

    # API responses: no caching
    if path.startswith("/v1/"):
        response.headers["Cache-Control"] = (
            "private, no-cache, no-store, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    else:
        response.headers["Cache-Control"] = "public, max-age=86400"

    return response


app.middleware("http")(add_cache_control_headers)


# ── Validation error handler ────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log request body on 422 validation errors to aid debugging."""
    try:
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace") if body else "(empty)"
    except Exception:
        body_str = "(could not read body)"
    logger.error(
        "422 ValidationError on %s %s: errors=%r body=%r",
        request.method,
        request.url.path,
        exc.errors(),
        body_str[:500],
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# ── ルーター登録 ───────────────────────────────────────────────────────────
app.include_router(solve.router)
if learning is not None:
    app.include_router(learning.router)
else:
    logger.warning("Learning router is unavailable and will be skipped")


# ── Health Check ───────────────────────────────────────────────────────────
@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    """Root endpoint — returns cloud provider info."""
    if powertools_available:
        metrics.add_metric(name="RootEndpointCalled", unit=MetricUnit.Count, value=1)

    return HealthResponse(
        status="ok",
        provider=settings.cloud_provider.value,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    if powertools_available:
        metrics.add_metric(name="HealthCheckCalled", unit=MetricUnit.Count, value=1)

    logger.info(
        "Health check requested", extra={"provider": settings.cloud_provider.value}
    )

    return HealthResponse(
        status="ok",
        provider=settings.cloud_provider.value,
    )


# AWS Lambda handler (Mangum)
try:
    from mangum import Mangum

    _mangum_handler = Mangum(app, lifespan="off")

    if powertools_available:

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
