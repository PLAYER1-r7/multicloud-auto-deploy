from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from mangum import Mangum

from app.routers import auth, views

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

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(views.router)


@app.get("/health", name="health")
def health() -> dict:
    return {"status": "ok"}
