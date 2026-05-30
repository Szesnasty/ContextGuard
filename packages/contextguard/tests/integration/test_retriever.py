"""Hybrid retriever integration tests (Milestone B1.4, ADR-001).

Opt-in: require the compose stack (`make up`) and a pulled embedding model.
They SKIP when the stack is down so `make test` stays green offline (ADR-010).

    make up && uv run pytest packages/contextguard/tests/integration -m integration
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


def _chunk(chunk_id: str, text: str, *, tenant: str = "acme") -> Chunk:
    return Chunk(
        id=chunk_id,
        doc_id="doc-1",
        tenant=tenant,
        text=text,
        classification=Classification.INTERNAL,
    )


# A corpus where one chunk hides a rare identifier that semantic search blurs.
_CHUNKS = [
    _chunk("c1", "the quarterly revenue report for the finance team"),
    _chunk("c2", "a poem about the ocean and a quiet morning walk"),
    _chunk("c3", "incident postmortem mentioning token EXFIL-TOKEN-9000 leaked"),
    _chunk("c4", "the cat sat on the mat in the warm afternoon sun"),
    _chunk("c5", "annual financial projections and budget planning notes"),
]


@pytest.fixture
def embedder():
    from contextguard.retrieval.embeddings import OllamaEmbedder

    return OllamaEmbedder()


@pytest.fixture
def retriever(embedder):
    from contextguard.retrieval.bm25 import BM25Index
    from contextguard.retrieval.retriever import HybridRetriever
    from contextguard.retrieval.store import create_schema, get_engine, upsert_chunks

    engine = get_engine()
    create_schema(engine)
    with engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(text("TRUNCATE TABLE chunks"))
    upsert_chunks(engine, _CHUNKS, embedder)
    index = BM25Index(_CHUNKS)
    yield HybridRetriever(engine, embedder, index, alpha=0.5, candidates=10)
    engine.dispose()


@requires_stack
def test_hybrid_finds_exact_identifier(retriever) -> None:
    # A rare token is BM25's strength; hybrid must surface it near the top.
    hits = retriever.retrieve("EXFIL-TOKEN-9000", k=3)
    assert "c3" in {hit.id for hit in hits}
    assert hits[0].id == "c3"


@requires_stack
def test_hybrid_finds_semantic_match(retriever) -> None:
    # No shared keywords with c1/c5, but semantically about finance.
    hits = retriever.retrieve("company earnings and money", k=3)
    assert {"c1", "c5"} & {hit.id for hit in hits}


@requires_stack
def test_retrieve_k_bound(retriever) -> None:
    hits = retriever.retrieve("the", k=2)
    assert len(hits) <= 2


@requires_stack
def test_retrieve_returns_full_chunk_data(retriever) -> None:
    hit = retriever.retrieve("EXFIL-TOKEN-9000", k=1)[0]
    assert hit.tenant == "acme"
    assert hit.classification == str(Classification.INTERNAL)
    assert "EXFIL-TOKEN-9000" in hit.text


@requires_stack
def test_hybrid_recall_at_least_single_methods(retriever) -> None:
    from contextguard.retrieval.store import knn

    query = "EXFIL-TOKEN-9000 leaked token"
    target = "c3"

    # Dense alone (k=3).
    dense_vec = retriever._embedder.embed([query])[0]
    dense_ids = {hit.id for hit in knn(retriever._engine, dense_vec, k=3)}
    bm25_ids = {chunk_id for chunk_id, _ in retriever._index.search(query, k=3)}
    hybrid_ids = {hit.id for hit in retriever.retrieve(query, k=3)}

    dense_recall = int(target in dense_ids)
    bm25_recall = int(target in bm25_ids)
    hybrid_recall = int(target in hybrid_ids)
    assert hybrid_recall >= max(dense_recall, bm25_recall)
