"""ASGI app for GCP Cloud Functions"""
from app.main import app

# This is the ASGI app that Cloud Run will directly call
__all__ = ['app']
