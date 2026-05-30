"""Wire a live :class:`HybridRetriever` from the seeded pgvector store (B1.6).

Tier A (ADR-010): pulls SQLAlchemy + the embedder, so import it explicitly. The
BM25 index is built from whatever chunks are already in pgvector (via
:func:`~contextguard.retrieval.store.all_chunks`), so the dense and keyword
halves index the same set without a second corpus source - the database is the
single source of seeded chunks.
"""

from __future__ import annotations

from contextguard.retrieval.bm25 import BM25Index
from contextguard.retrieval.embeddings import Embedder, get_embedder
from contextguard.retrieval.rerank import get_reranker
from contextguard.retrieval.retriever import HybridRetriever
from contextguard.retrieval.store import all_chunks, get_engine


def build_retriever(*, embedder: Embedder | None = None) -> HybridRetriever:
    """Build a retriever over the seeded store (engine + embedder from env).

    The reranker is selected from ``RERANKER`` (``none`` by default, ADR-016);
    when configured it narrows the hybrid candidate pool to the final top-k
    before policy + redaction.
    """
    engine = get_engine()
    resolved = embedder or get_embedder()
    index = BM25Index(all_chunks(engine))
    return HybridRetriever(engine, resolved, index, reranker=get_reranker())


__all__ = ["build_retriever"]
