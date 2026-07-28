"""
Gunicorn configuration file for Render / Cloud deployment.
Configures Gunicorn to use UvicornWorker for ASGI & WebSocket compatibility.
"""

worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:10000"
workers = 1
