"""Reranker integration tests (Milestone B3.4, ADR-016).

Two opt-in proofs over the live compose stack (`make up`):

1. the retriever wires the rerank stage - a fake cross-encoder reorders the
   fused pool and the final result is narrowed to top-k (no torch needed);
2. the real ``bge-reranker-base`` loads and surfaces the relevant chunk to the
   top (skips when the [rerank] extra / model is unavailable).

Both SKIP when the stack is down so `make test` stays green offline (ADR-010).
"""

from __future__ import annotations

import socket

import pytest
from contextguard_contracts.enums import Classification
from contextguard_contracts.models import Chunk

pytestmark = pytest.mark.integration

PG_PORT = 5432
OLLAMA_PORT = 11434


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


requires_stack = pytest.mark.skipif(
    not (_port_open("localhost", PG_PORT) and _port_open("localhost", OLLAMA_PORT)),
    reason="local compose stack not running (run `make up`)",
)


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        doc_id="doc-1",
        tenant="acme",
        text=text,
        classification=Classification.INTERNAL,
    )


_CHUNKS = [
    _chunk("c1", "the quarterly revenue report for the finance team"),
    _chunk("c2", "a poem about the ocean and a quiet morning walk"),
    _chunk("c3", "the refund policy lets customers return an item within 30 days"),
    _chunk("c4", "the cat sat on the mat in the warm afternoon sun"),
    _chunk("c5", "annual financial projections and budget planning notes"),
]


class _KeywordReranker:
    """Deterministic fake cross-encoder: scores by query-token overlap."""

    model = "fake-keyword"

    def score(self, query: str, documents: list[str]) -> list[float]:
        terms = set(query.lower().split())
        return [float(len(terms & set(doc.lower().split()))) for doc in documents]


@pytest.fixture
def embedder():
    from contextguard.retrieval.embeddings import OllamaEmbedder

    return OllamaEmbedder()


def _seed_index(embedder):
    from contextguard.retrieval.bm25 import BM25Index
    from contextguard.retrieval.store import create_schema, get_engine, upsert_chunks
    from sqlalchemy import text

    engine = get_engine()
    create_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE chunks"))
    upsert_chunks(engine, _CHUNKS, embedder)
    return engine, BM25Index(_CHUNKS)


@requires_stack
def test_retriever_applies_reranker_and_narrows_to_k(embedder) -> None:
    from contextguard.retrieval.retriever import HybridRetriever

    engine, index = _seed_index(embedder)
    try:
        retriever = HybridRetriever(
            engine,
            embedder,
            index,
            reranker=_KeywordReranker(),
            rerank_pool=10,
        )
        hits = retriever.retrieve("refund policy return item", k=2)
        # The fake cross-encoder must lift the lexically-matching refund chunk to
        # the very top, and the result is narrowed to the requested k.
        assert len(hits) <= 2
        assert hits[0].id == "c3"
    finally:
        engine.dispose()


@requires_stack
def test_real_bge_reranker_surfaces_relevant_chunk(embedder) -> None:
    pytest.importorskip(
        "sentence_transformers",
        reason="install the [rerank] extra to run the real cross-encoder",
    )
    from contextguard.retrieval.rerank import CrossEncoderReranker
    from contextguard.retrieval.retriever import HybridRetriever

    engine, index = _seed_index(embedder)
    try:
        retriever = HybridRetriever(
            engine,
            embedder,
            index,
            reranker=CrossEncoderReranker(),
            rerank_pool=10,
        )
        hits = retriever.retrieve("how long do I have to return a purchase?", k=3)
        assert "c3" in {hit.id for hit in hits}
        # The cross-encoder reads the (query, chunk) pair, so the refund chunk
        # should win the top slot even though it shares no rare keyword.
        assert hits[0].id == "c3"
    finally:
        engine.dispose()
