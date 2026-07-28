"""
Application configuration loaded from environment variables.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from the backend directory
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")


class Settings(BaseSettings):
    """Voice bot configuration."""

    # Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv(
        "GEMINI_MODEL", "gemini-3.1-flash-live-preview"
    )
    voice_name: str = os.getenv("VOICE_NAME", "Kore")

    # Paths
    backend_dir: Path = _backend_dir
    data_dir: Path = _backend_dir / "data"
    vectorstore_dir: Path = _backend_dir / "vectorstore"
    portfolio_path: Path = _backend_dir / "data" / "portfolio.md"

    # RAG
    chunk_size: int = 500
    chunk_overlap: int = 50
    retrieval_k: int = 5

    # Embedding model
    embedding_model: str = "models/text-embedding-004"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
