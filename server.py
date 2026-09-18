"""
Root entry point for cloud deployments (Render, Railway, Heroku).
Exposes `app` for WSGI/ASGI servers running `gunicorn server:app` or `uvicorn server:app`.
"""

from app.main import app  # noqa: F401
