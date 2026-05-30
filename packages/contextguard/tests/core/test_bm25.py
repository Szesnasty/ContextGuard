"""BM25 keyword index tests (Milestone B1.4, ADR-001). Pure-Python, zero-infra."""

from __future__ import annotations

from dataclasses import dataclass

from contextguard.retrieval.bm25 import BM25Index


@dataclass(frozen=True)
class _Doc:
    id: str
    text: str


_CORPUS = [
    _Doc("c1", "the quarterly revenue report for the finance team"),
    _Doc("c2", "a poem about the ocean and the quiet morning"),
    _Doc("c3", "incident postmortem mentioning token EXFIL-TOKEN-9000 leaked"),
    _Doc("c4", "the cat sat on the mat in the warm sun"),
]


def test_exact_identifier_ranks_first() -> None:
    index = BM25Index(_CORPUS)
    hits = index.search("EXFIL-TOKEN-9000", k=5)
    assert hits  # the rare identifier is found
    assert hits[0][0] == "c3"


def test_empty_index_returns_empty() -> None:
    index = BM25Index([])
    assert index.search("anything", k=5) == []
    assert len(index) == 0


def test_empty_query_returns_empty() -> None:
    index = BM25Index(_CORPUS)
    assert index.search("", k=5) == []
    assert index.search("   ", k=5) == []


def test_k_bound() -> None:
    index = BM25Index(_CORPUS)
    hits = index.search("the", k=2)
    assert len(hits) <= 2


def test_non_positive_k_returns_empty() -> None:
    index = BM25Index(_CORPUS)
    assert index.search("the", k=0) == []


def test_deterministic_and_finite_scores() -> None:
    index = BM25Index(_CORPUS)
    first = index.search("quarterly revenue", k=5)
    second = index.search("quarterly revenue", k=5)
    assert first == second
    assert all(score > 0 for _, score in first)


def test_only_matching_chunks_returned() -> None:
    index = BM25Index(_CORPUS)
    hits = index.search("postmortem", k=5)
    # Only c3 contains "postmortem"; unrelated chunks score zero and drop out.
    assert [chunk_id for chunk_id, _ in hits] == ["c3"]


def test_get_returns_indexed_chunk() -> None:
    index = BM25Index(_CORPUS)
    assert index.get("c1") is _CORPUS[0]
    assert index.get("missing") is None
