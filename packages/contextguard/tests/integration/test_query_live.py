"""End-to-end ``/v1/query`` integration test (Milestone B1.6).

Opt-in: requires the compose stack (`make up`) with the embedding + chat models
pulled. SKIPS when the stack is down so `make test` stays green offline (ADR-010).
Exercises the real path: seed pgvector -> retrieve -> guard -> build_prompt ->
live Ollama -> grounded answer.

    make up && uv run pytest packages/contextguard/tests/integration -m integration
"""

from __future__ import annotations

import socket

import pytest
from contextguard_contracts.enums import Classification
from contextguard_contracts.models import Chunk
from fastapi.testclient import TestClient

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

_CHUNKS = [
    Chunk(
        id="falcon-1",
        doc_id="acme-mna-falcon",
        tenant="acme",
        text="The launch code for Project Falcon is FALCON-7788. Keep it confidential.",
        classification=Classification.CONFIDENTIAL,
    ),
    Chunk(
        id="weather-1",
        doc_id="acme-notes",
        tenant="acme",
        text="The weather in the harbour was calm and clear this morning.",
        classification=Classification.INTERNAL,
    ),
]

_USER = {"sub": "u1", "tenant": "acme", "role": "exec", "purpose": "review"}


@pytest.fixture
def live_client():
    from contextguard.api.app import create_app
    from contextguard.api.deps import get_retriever
    from contextguard.retrieval.bm25 import BM25Index
    from contextguard.retrieval.embeddings import OllamaEmbedder
    from contextguard.retrieval.retriever import HybridRetriever
    from contextguard.retrieval.store import create_schema, get_engine, upsert_chunks
    from sqlalchemy import text

    engine = get_engine()
    create_schema(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE chunks"))
    embedder = OllamaEmbedder()
    upsert_chunks(engine, _CHUNKS, embedder)
    retriever = HybridRetriever(engine, embedder, BM25Index(_CHUNKS), candidates=10)

    app = create_app()
    app.dependency_overrides[get_retriever] = lambda: retriever
    with TestClient(app) as client:
        yield client
    engine.dispose()


@requires_stack
def test_query_end_to_end_grounded_answer(live_client: TestClient) -> None:
    resp = live_client.post(
        "/v1/query",
        json={"query": "What is the launch code for Project Falcon?", "user": _USER, "k": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Retrieval found the planted chunk; pass-through guard let it through; the
    # live model repeated the confidential code from context -> the leak is real.
    assert any(h["id"] == "falcon-1" for h in body["retrieved_chunks"])
    assert body["guarded_context"]["allowed_chunks"]
    assert "FALCON-7788" in body["answer"]
