"""Retrieval adapters (hybrid search, pgvector, BM25). Filled in phase 2.

The chunker (`chunking`) is pure and zero-infra; heavier adapters (embedder,
pgvector store, BM25) arrive with their `[pgvector]` extras in later B1 steps.
"""

from __future__ import annotations

from contextguard.retrieval.chunking import (
    Chunker,
    FixedSizeChunker,
    SourceDocument,
    chunk_corpus,
)

__all__ = ["Chunker", "FixedSizeChunker", "SourceDocument", "chunk_corpus"]
