"""Reranker stage: pure, zero-infra unit tests (Milestone B3.4, ADR-016).

These exercise the cross-encoder *stage* (selection + ordering + truncation)
without a model or a DB: a fake reranker supplies scores and a local dataclass
stands in for ``RetrievedChunk`` so the test never imports the SQLAlchemy-backed
retriever. The real ``bge-reranker-base`` is covered opt-in in integration.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from contextguard.retrieval.rerank import (
    CrossEncoderReranker,
    NoOpReranker,
    Reranker,
    get_reranker,
    rerank_chunks,
    rerank_pool_size,
)


@dataclass(frozen=True)
class _Doc:
    """Minimal stand-in for ``RetrievedChunk`` (id + text + score)."""

    id: str
    text: str
    score: float = 0.0


class _ScriptedReranker:
    """Returns relevance scores keyed by chunk text (test double)."""

    model = "scripted"

    def __init__(self, scores: dict[str, float]) -> None:
        self._scores = scores

    def score(self, query: str, documents: list[str]) -> list[float]:
        return [self._scores[doc] for doc in documents]


def _docs(*texts: str) -> list[_Doc]:
    return [_Doc(id=f"c{i}", text=t) for i, t in enumerate(texts)]


def test_noop_reranker_preserves_input_order() -> None:
    docs = _docs("first", "second", "third")
    out = rerank_chunks(NoOpReranker(), "q", docs, top_k=3)
    assert [d.id for d in out] == ["c0", "c1", "c2"]


def test_rerank_reorders_by_relevance_score() -> None:
    docs = _docs("low", "high", "mid")
    reranker = _ScriptedReranker({"low": 0.1, "high": 0.9, "mid": 0.5})
    out = rerank_chunks(reranker, "q", docs, top_k=3)
    assert [d.text for d in out] == ["high", "mid", "low"]


def test_rerank_truncates_to_top_k() -> None:
    docs = _docs("a", "b", "c", "d", "e")
    reranker = _ScriptedReranker({"a": 0.1, "b": 0.9, "c": 0.5, "d": 0.7, "e": 0.2})
    out = rerank_chunks(reranker, "q", docs, top_k=2)
    assert [d.text for d in out] == ["b", "d"]
    assert len(out) == 2


def test_rerank_writes_relevance_into_score() -> None:
    docs = _docs("only")
    out = rerank_chunks(_ScriptedReranker({"only": 0.42}), "q", docs, top_k=1)
    assert out[0].score == pytest.approx(0.42)


def test_rerank_tie_break_is_deterministic_by_id() -> None:
    docs = [_Doc(id="z", text="x"), _Doc(id="a", text="y")]
    reranker = _ScriptedReranker({"x": 0.5, "y": 0.5})
    out = rerank_chunks(reranker, "q", docs, top_k=2)
    assert [d.id for d in out] == ["a", "z"]


def test_rerank_empty_is_empty() -> None:
    assert rerank_chunks(NoOpReranker(), "q", [], top_k=5) == []


def test_noop_score_is_strictly_decreasing() -> None:
    scores = NoOpReranker().score("q", ["a", "b", "c"])
    assert scores == [3.0, 2.0, 1.0]


def test_get_reranker_default_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RERANKER", raising=False)
    assert get_reranker() is None


@pytest.mark.parametrize("value", ["none", "off", "NONE"])
def test_get_reranker_disabled_values_return_none(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RERANKER", value)
    assert get_reranker() is None


@pytest.mark.parametrize("value", ["cross-encoder", "bge", "BGE"])
def test_get_reranker_selects_cross_encoder(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RERANKER", value)
    reranker = get_reranker()
    assert isinstance(reranker, CrossEncoderReranker)
    assert isinstance(reranker, Reranker)


def test_get_reranker_unknown_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RERANKER", "cohere")
    with pytest.raises(ValueError, match="unknown RERANKER backend"):
        get_reranker()


def test_cross_encoder_default_model_is_bge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RERANKER_MODEL", raising=False)
    assert CrossEncoderReranker().model == "BAAI/bge-reranker-base"


def test_cross_encoder_model_override_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RERANKER_MODEL", "BAAI/bge-reranker-large")
    assert CrossEncoderReranker().model == "BAAI/bge-reranker-large"


def test_rerank_pool_size_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RERANK_POOL", raising=False)
    assert rerank_pool_size() == 50
    monkeypatch.setenv("RERANK_POOL", "30")
    assert rerank_pool_size() == 30
