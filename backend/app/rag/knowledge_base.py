"""
Knowledge base builder: loads portfolio documents, chunks them,
generates embeddings, and persists a FAISS vector store.
"""

import hashlib
import json
import logging
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)

_CHECKSUM_FILE = "source_checksum.json"


def _file_checksum(path: Path) -> str:
    """Return the MD5 hex-digest of a file."""
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def _needs_rebuild(vectorstore_dir: Path, source_path: Path) -> bool:
    """Check whether the vector store needs to be rebuilt."""
    checksum_path = vectorstore_dir / _CHECKSUM_FILE
    if not checksum_path.exists():
        return True
    try:
        stored = json.loads(checksum_path.read_text())
        return stored.get("checksum") != _file_checksum(source_path)
    except Exception:
        return True


def _save_checksum(vectorstore_dir: Path, source_path: Path) -> None:
    """Persist the source file checksum."""
    checksum_path = vectorstore_dir / _CHECKSUM_FILE
    checksum_path.write_text(
        json.dumps({"checksum": _file_checksum(source_path)})
    )


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Return the configured embedding model."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.gemini_api_key,
    )


def build_knowledge_base(force: bool = False) -> FAISS:
    """
    Build (or rebuild) the FAISS vector store from the portfolio document.

    Args:
        force: If True, rebuild even if the source hasn't changed.

    Returns:
        The FAISS vector store instance.
    """
    vs_dir = settings.vectorstore_dir
    src = settings.portfolio_path

    if not src.exists():
        raise FileNotFoundError(f"Portfolio source not found: {src}")

    # Check if rebuild is needed
    if not force and vs_dir.exists() and not _needs_rebuild(vs_dir, src):
        logger.info("Vector store is up-to-date, loading from disk.")
        return FAISS.load_local(
            str(vs_dir), get_embeddings(), allow_dangerous_deserialization=True
        )

    logger.info("Building vector store from %s ...", src)

    # 1. Load document
    loader = TextLoader(str(src), encoding="utf-8")
    documents = loader.load()

    # 2. Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n### ", "\n- ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info("Created %d chunks from portfolio.", len(chunks))

    # 3. Create embeddings + FAISS index
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # 4. Persist
    vs_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(vs_dir))
    _save_checksum(vs_dir, src)
    logger.info("Vector store saved to %s", vs_dir)

    return vectorstore


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    vs = build_knowledge_base(force=True)
    print(f"Knowledge base built successfully with {vs.index.ntotal} vectors.")
