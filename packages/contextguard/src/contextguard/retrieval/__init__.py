"""Retrieval adapters (hybrid search, pgvector, BM25). Filled in phase 2.

The chunker (`chunking`) is pure and zero-infra; heavier adapters (embedder,
pgvector store, BM25) arrive with their `[pgvector]` extras in later B1 steps.

The embedder interface is exported here (its module is light at import time -
the HTTP/OpenAI clients load lazily). The pgvector store pulls SQLAlchemy at
import, so import it explicitly via ``contextguard.retrieval.store`` to keep
``import contextguard.retrieval`` zero-infra.
"""

from __future__ import annotations

from contextguard.retrieval.chunking import (
    Chunker,
    FixedSizeChunker,
    SourceDocument,
    chunk_corpus,
)
from contextguard.retrieval.embeddings import (
    CloudEmbedder,
    Embedder,
    OllamaEmbedder,
    Vector,
    get_embedder,
)

__all__ = [
    "Chunker",
    "CloudEmbedder",
    "Embedder",
    "FixedSizeChunker",
    "OllamaEmbedder",
    "SourceDocument",
    "Vector",
    "chunk_corpus",
    "get_embedder",
]
