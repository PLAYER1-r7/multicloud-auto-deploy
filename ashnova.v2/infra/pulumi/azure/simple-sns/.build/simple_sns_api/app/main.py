from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import posts, profile, uploads

app = FastAPI(title="Simple SNS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)
app.include_router(uploads.router)
app.include_router(profile.router)


@app.get("/")
def root() -> dict:
    return {"status": "ok"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
