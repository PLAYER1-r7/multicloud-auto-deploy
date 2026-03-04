"""Export FastAPI app for Cloud Run"""
from app.main import app

# Export for uvicorn/gunicorn
__all__ = ['app']
