"""
Root entry point for cloud deployments (Render, Railway, Heroku).
Exposes `app` for WSGI/ASGI servers running `gunicorn server:app` or `uvicorn server:app`.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path so 'app' package is found
_backend_dir = Path(__file__).resolve().parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.main import app  # noqa: F401
