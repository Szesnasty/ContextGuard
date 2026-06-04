"""Cross-encoder reranking behind one interface (Milestone B3.4, ADR-016).

Hybrid retrieval (ADR-001) fuses two *bi-encoder* rankings: the query and each
chunk are embedded independently, so relevance is only ever approximated by
vector proximity. A **cross-encoder** instead reads the query and a candidate
*together* and scores the pair directly - far more accurate, but too expensive
to run over the whole corpus. So it goes second: hybrid retrieval proposes a
wide candidate pool (top-N), the reranker reads each (query, chunk) pair, and
only the top-K survive into policy + redaction (ADR-005). The small reranked set
is what keeps the downstream PII/redaction cost bounded.

Two backends, one :class:`Reranker` protocol - the same shape as
:class:`~contextguard.retrieval.embeddings.Embedder`:

* :class:`NoOpReranker` - the **default**. Keeps the hybrid order untouched, so
  the library stays zero-infra and ``make test`` runs offline (ADR-010). A
  no-rerank pipeline is a worse pipeline, not a broken one.
* :class:`CrossEncoderReranker` - the real ``bge-reranker-base`` cross-encoder
  backend, loaded lazily via ``sentence-transformers`` from the opt-in
  ``[rerank]`` extra. ``torch`` never enters the library process until a
  cross-encoder is actually constructed and used.

The backend is chosen by the ``RERANKER`` environment variable (``none`` by
default). :func:`rerank_chunks` is the pure, infra-free stage applied to already
retrieved chunks, so it is unit-testable with a fake reranker and no DB/model.
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from contextguard.retrieval.retriever import RetrievedChunk

# bge-reranker-base reads up to 512 tokens per pair; the default top-N pool the
# hybrid stage hands over before the cross-encoder narrows it to top-k.
_DEFAULT_RERANK_POOL = 50
_DEFAULT_MODEL = "BAAI/bge-reranker-base"


@runtime_checkable
class Reranker(Protocol):
    """Scores ``(query, document)`` pairs; higher means more relevant."""

    @property
    def model(self) -> str: ...

    def score(self, query: str, documents: list[str]) -> list[float]: ...


class NoOpReranker:
    """Identity reranker (default): returns order-preserving scores, no infra."""

    model = "noop"

    def score(self, query: str, documents: list[str]) -> list[float]:
        # Strictly decreasing so a stable sort by descending score preserves the
        # incoming hybrid order exactly.
        return [float(len(documents) - i) for i in range(len(documents))]


class CrossEncoderReranker:
    """Real cross-encoder (``bge-reranker-base``) via ``sentence-transformers``.

    The heavy encoder (and ``torch``) is constructed lazily on first
    :meth:`score`, so importing this module - or selecting the backend - never
    pulls the model until a rerank actually runs.
    """

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model or os.getenv("RERANKER_MODEL") or _DEFAULT_MODEL
        self._encoder: Any = None

    @property
    def model(self) -> str:
        return self._model

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        if self._encoder is None:
            from sentence_transformers import CrossEncoder

            self._encoder = CrossEncoder(self._model)
        pairs = [[query, doc] for doc in documents]
        scores = self._encoder.predict(pairs)
        return [float(s) for s in scores]


def get_reranker() -> Reranker | None:
    """Return the configured reranker, or ``None`` for no reranking (default).

    ``RERANKER`` selects the backend: ``none`` (default) disables reranking and
    keeps the pipeline zero-infra; ``cross-encoder`` (alias ``bge``) loads the
    ``bge-reranker-base`` cross-encoder from the ``[rerank]`` extra.
    """
    backend = os.getenv("RERANKER", "none").lower()
    if backend in {"none", "off", ""}:
        return None
    if backend in {"cross-encoder", "bge", "local"}:
        return CrossEncoderReranker()
    msg = f"unknown RERANKER backend {backend!r} (expected 'none' or 'cross-encoder')"
    raise ValueError(msg)


def rerank_pool_size() -> int:
    """The top-N pool the hybrid stage hands to the reranker (``RERANK_POOL``)."""
    raw = os.getenv("RERANK_POOL")
    return int(raw) if raw else _DEFAULT_RERANK_POOL


def rerank_chunks(
    reranker: Reranker,
    query: str,
    chunks: list[RetrievedChunk],
    *,
    top_k: int,
) -> list[RetrievedChunk]:
    """Reorder ``chunks`` by cross-encoder relevance and keep the top ``top_k``.

    Pure and infra-free: it only calls ``reranker.score`` over the chunk texts,
    then sorts descending (id breaks ties for determinism) and truncates. Each
    returned chunk carries its rerank score in ``score``, so the value the
    downstream sees is the cross-encoder relevance, not the fused rank.
    """
    if not chunks:
        return []
    scores = reranker.score(query, [chunk.text for chunk in chunks])
    ranked = sorted(
        zip(chunks, scores, strict=True),
        key=lambda pair: (-pair[1], pair[0].id),
    )
    return [replace(chunk, score=float(score)) for chunk, score in ranked[: max(top_k, 0)]]


__all__ = [
    "CrossEncoderReranker",
    "NoOpReranker",
    "Reranker",
    "get_reranker",
    "rerank_chunks",
    "rerank_pool_size",
]
