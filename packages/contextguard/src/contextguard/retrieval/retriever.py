"""Hybrid retriever: dense kNN + BM25, fused (Milestone B1.4, ADR-001).

Orchestrates the two halves of ADR-001 into one call. Dense kNN (pgvector,
ADR-008) finds semantically similar chunks; BM25 (``bm25``) finds exact keyword
matches; :func:`~contextguard.retrieval.hybrid.reciprocal_rank_fusion` merges
their rankings with a configurable ``alpha``.

This module pulls the SQLAlchemy-backed store, so import it explicitly via
``contextguard.retrieval.retriever`` to keep ``import contextguard.retrieval``
zero-infra (ADR-010). The ``filters`` argument on :meth:`HybridRetriever.retrieve`
is wired now but unused until the phase-4 policy push-down.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import Engine

from contextguard.retrieval.bm25 import BM25Index
from contextguard.retrieval.embeddings import Embedder
from contextguard.retrieval.hybrid import reciprocal_rank_fusion
from contextguard.retrieval.store import Neighbour, knn

# Defaults mirror the embeddings module: env-overridable, no central settings.
_DEFAULT_ALPHA = 0.5
_DEFAULT_CANDIDATES = 10


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


@dataclass(frozen=True)
class RetrievedChunk:
    """One hybrid hit: the chunk's identity, its text, and the fused score."""

    id: str
    doc_id: str
    tenant: str
    classification: str
    text: str
    score: float
    metadata: dict[str, str]


class HybridRetriever:
    """Dense kNN + BM25 fused into one ranked list (ADR-001)."""

    def __init__(
        self,
        engine: Engine,
        embedder: Embedder,
        index: BM25Index,
        *,
        alpha: float | None = None,
        candidates: int | None = None,
    ) -> None:
        self._engine = engine
        self._embedder = embedder
        self._index = index
        self._alpha = alpha if alpha is not None else _env_float("RETRIEVAL_ALPHA", _DEFAULT_ALPHA)
        self._candidates = (
            candidates
            if candidates is not None
            else _env_int("RETRIEVAL_CANDIDATES", _DEFAULT_CANDIDATES)
        )

    def retrieve(
        self,
        query: str,
        k: int = 5,
        filters: Mapping[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        """Return up to ``k`` chunks for ``query``, dense + BM25 fused.

        Each retriever contributes ``candidates`` results; the fusion keeps the
        top ``k``. ``filters`` is forwarded to the dense kNN (unused until phase
        4). The result text/metadata come from the dense hit when available, else
        from the BM25 index.
        """
        query_vector = self._embedder.embed([query])[0]
        dense: list[Neighbour] = knn(
            self._engine, query_vector, k=self._candidates, filters=filters
        )
        keyword = self._index.search(query, k=self._candidates)

        fused = reciprocal_rank_fusion(
            [hit.id for hit in dense],
            [chunk_id for chunk_id, _ in keyword],
            alpha=self._alpha,
            k=k,
        )

        dense_by_id = {hit.id: hit for hit in dense}
        results: list[RetrievedChunk] = []
        for chunk_id, score in fused:
            hit = dense_by_id.get(chunk_id)
            if hit is not None:
                results.append(
                    RetrievedChunk(
                        id=hit.id,
                        doc_id=hit.doc_id,
                        tenant=hit.tenant,
                        classification=hit.classification,
                        text=hit.text,
                        score=score,
                        metadata=dict(hit.metadata),
                    )
                )
                continue
            chunk = self._index.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                RetrievedChunk(
                    id=chunk.id,
                    doc_id=getattr(chunk, "doc_id", ""),
                    tenant=getattr(chunk, "tenant", ""),
                    classification=str(getattr(chunk, "classification", "")),
                    text=chunk.text,
                    score=score,
                    metadata=dict(getattr(chunk, "metadata", {}) or {}),
                )
            )
        return results


__all__ = ["HybridRetriever", "RetrievedChunk"]
