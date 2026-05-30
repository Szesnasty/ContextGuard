"""Retrieval adapters (hybrid search, pgvector, BM25). Filled in phase 2.

The chunker (`chunking`) is pure and zero-infra; heavier adapters (embedder,
pgvector store, BM25) arrive with their `[pgvector]` extras in later B1 steps.

The embedder interface plus the BM25 keyword index and the hybrid rank fusion
are exported here (all light at import time - the HTTP/OpenAI clients load
lazily, and BM25/fusion are pure-Python). The pgvector store and the
`HybridRetriever` pull SQLAlchemy at import, so import them explicitly via
``contextguard.retrieval.store`` / ``contextguard.retrieval.retriever`` to keep
``import contextguard.retrieval`` zero-infra.
"""

from __future__ import annotations

from contextguard.retrieval.bm25 import BM25Index, KeywordSearcher
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
from contextguard.retrieval.hybrid import reciprocal_rank_fusion

__all__ = [
    "BM25Index",
    "Chunker",
    "CloudEmbedder",
    "Embedder",
    "FixedSizeChunker",
    "KeywordSearcher",
    "OllamaEmbedder",
    "SourceDocument",
    "Vector",
    "chunk_corpus",
    "get_embedder",
    "reciprocal_rank_fusion",
]
