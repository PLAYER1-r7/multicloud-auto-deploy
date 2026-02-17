from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from app.routers import auth, views

app = FastAPI(title="Simple SNS Web")

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(views.router)


@app.get("/health", name="health")
def health() -> dict:
    return {"status": "ok"}
