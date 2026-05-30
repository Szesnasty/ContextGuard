"""Pure-Python BM25 keyword search (Milestone B1.4, ADR-001).

The dense embedder (ADR-008) misses exact identifiers - product codes, ticket
numbers, tokens - because semantic similarity blurs them. BM25 is the keyword
half of the hybrid retriever (ADR-001): it ranks a chunk by how rare and how
frequent the query's terms are inside it.

Design choice (consistent with the tokenizer decision in ``core.tokens`` and the
zero-infra tiers of ADR-010): the index is a small, deterministic, dependency
free Okapi BM25 built on the **same** regex tokenizer the chunker and token
counter use. That keeps keyword search in the zero-infra core test tier (no
network, no numpy), guarantees identical tokenization across the pipeline, and
stays fully reproducible. ``rank_bm25`` (numpy) or a Postgres ``tsvector`` index
(ADR-009) are documented production-scale swaps behind the same
:class:`KeywordSearcher` protocol - not the default.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from contextguard.core.tokens import token_spans

# Okapi BM25 defaults (the Lucene/Elasticsearch values).
_DEFAULT_K1 = 1.5
_DEFAULT_B = 0.75


@runtime_checkable
class TextChunk(Protocol):
    """The minimal shape BM25 needs: a stable id and the text to index."""

    @property
    def id(self) -> str: ...

    @property
    def text(self) -> str: ...


@runtime_checkable
class KeywordSearcher(Protocol):
    """Anything that ranks chunk ids by keyword relevance to a query."""

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]: ...


def _tokenize(text: str) -> list[str]:
    """Lowercased tokens via the shared core tokenizer (same as the chunker)."""
    return [text[start:end].lower() for start, end in token_spans(text)]


class BM25Index:
    """In-memory Okapi BM25 index over chunk texts (deterministic, offline)."""

    def __init__(
        self,
        chunks: Sequence[TextChunk],
        *,
        k1: float = _DEFAULT_K1,
        b: float = _DEFAULT_B,
    ) -> None:
        if k1 < 0:
            raise ValueError("k1 must be non-negative")
        if not 0 <= b <= 1:
            raise ValueError("b must be in [0, 1]")
        self._k1 = k1
        self._b = b
        self._chunks: dict[str, TextChunk] = {chunk.id: chunk for chunk in chunks}
        self._ids: list[str] = [chunk.id for chunk in chunks]
        self._freqs: dict[str, Counter[str]] = {}
        self._lengths: dict[str, int] = {}
        doc_freq: Counter[str] = Counter()
        for chunk in chunks:
            terms = _tokenize(chunk.text)
            counts = Counter(terms)
            self._freqs[chunk.id] = counts
            self._lengths[chunk.id] = len(terms)
            doc_freq.update(counts.keys())
        self._n = len(self._ids)
        self._avgdl = (sum(self._lengths.values()) / self._n) if self._n else 0.0
        # Lucene-style idf: always positive, so scores never go negative or NaN.
        self._idf: dict[str, float] = {
            term: math.log(1 + (self._n - df + 0.5) / (df + 0.5)) for term, df in doc_freq.items()
        }

    def __len__(self) -> int:
        return self._n

    def get(self, chunk_id: str) -> TextChunk | None:
        """Return the indexed chunk for ``chunk_id`` (or ``None``)."""
        return self._chunks.get(chunk_id)

    def _score(self, chunk_id: str, query_terms: Sequence[str]) -> float:
        counts = self._freqs[chunk_id]
        length = self._lengths[chunk_id]
        denom_len = self._k1 * (1 - self._b + self._b * length / self._avgdl)
        score = 0.0
        for term in query_terms:
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            score += self._idf.get(term, 0.0) * (tf * (self._k1 + 1)) / (tf + denom_len)
        return score

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """Return up to ``k`` ``(chunk_id, score)`` pairs, best match first.

        Only chunks with a positive score (i.e. that contain a query term) are
        returned; ties break on chunk id so the order is deterministic.
        """
        if self._n == 0 or k <= 0:
            return []
        query_terms = _tokenize(query)
        if not query_terms:
            return []
        scored = [(chunk_id, self._score(chunk_id, query_terms)) for chunk_id in self._ids]
        scored = [(chunk_id, score) for chunk_id, score in scored if score > 0]
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:k]


__all__ = ["BM25Index", "KeywordSearcher", "TextChunk"]
