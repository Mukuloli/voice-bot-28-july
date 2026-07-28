"""
Retriever: loads the persisted FAISS index and performs
similarity search to provide context for the voice bot.
"""

import logging
from typing import Optional

from langchain_community.vectorstores import FAISS

from app.config import settings
from app.rag.knowledge_base import build_knowledge_base, get_embeddings

logger = logging.getLogger(__name__)

# Module-level cache for the vector store
_vectorstore: Optional[FAISS] = None


def get_vectorstore() -> FAISS:
    """Load or return the cached FAISS vector store."""
    global _vectorstore
    if _vectorstore is None:
        vs_dir = settings.vectorstore_dir
        if vs_dir.exists() and (vs_dir / "index.faiss").exists():
            logger.info("Loading vector store from disk.")
            _vectorstore = FAISS.load_local(
                str(vs_dir),
                get_embeddings(),
                allow_dangerous_deserialization=True,
            )
        else:
            logger.info("No persisted vector store found; building now.")
            _vectorstore = build_knowledge_base()
    return _vectorstore


def retrieve(query: str, k: Optional[int] = None) -> str:
    """
    Perform similarity search and return formatted context.

    Args:
        query: The search query from the user's question.
        k: Number of top results to retrieve.

    Returns:
        A formatted string of relevant portfolio information.
    """
    if k is None:
        k = settings.retrieval_k

    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=k)

    if not docs:
        return "No relevant information found in the portfolio."

    # Format results with clear separation
    sections = []
    for i, doc in enumerate(docs, 1):
        content = doc.page_content.strip()
        sections.append(f"[Source {i}]\n{content}")

    context = "\n\n---\n\n".join(sections)

    logger.info(
        "Retrieved %d chunks for query: '%s' (preview: %s...)",
        len(docs),
        query[:60],
        context[:100],
    )

    return context


def get_stats() -> dict:
    """Return statistics about the knowledge base."""
    try:
        vs = get_vectorstore()
        return {
            "status": "ready",
            "total_vectors": vs.index.ntotal,
            "source_file": str(settings.portfolio_path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
