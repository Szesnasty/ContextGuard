"""pgvector store integration tests (Milestone B1.3, ADR-008).

Opt-in: these require the compose stack (`make up`) and a pulled embedding model.
They SKIP when the stack is down so `make test` stays green offline (ADR-010).
Run explicitly:

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


@pytest.fixture
def engine():
    from contextguard.retrieval.store import create_schema, get_engine

    eng = get_engine()
    # Isolated table per run keeps the suite idempotent against a shared DB.
    create_schema(eng)
    with eng.begin() as conn:
        from sqlalchemy import text

        conn.execute(text("TRUNCATE TABLE chunks"))
    yield eng
    eng.dispose()


@pytest.fixture
def embedder():
    from contextguard.retrieval.embeddings import OllamaEmbedder

    return OllamaEmbedder()


@requires_stack
def test_live_embedder_dimension_and_deterministic(embedder) -> None:
    a = embedder.embed(["the quarterly revenue report"])
    b = embedder.embed(["the quarterly revenue report"])
    assert len(a) == 1
    assert len(a[0]) == embedder.dimension
    assert a == b  # local model is deterministic for the same input


@requires_stack
def test_upsert_and_count(engine, embedder) -> None:
    from contextguard.retrieval.store import upsert_chunks

    chunks = [_chunk("c1", "alpha document"), _chunk("c2", "beta document")]
    written = upsert_chunks(engine, chunks, embedder)
    assert written == 2


@requires_stack
def test_upsert_idempotent(engine, embedder) -> None:
    from contextguard.retrieval.store import upsert_chunks
    from sqlalchemy import text

    chunks = [_chunk("c1", "alpha document"), _chunk("c2", "beta document")]
    upsert_chunks(engine, chunks, embedder)
    upsert_chunks(engine, chunks, embedder)  # re-upsert must not duplicate
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM chunks")).scalar_one()
    assert count == 2


@requires_stack
def test_knn_self_neighbour(engine, embedder) -> None:
    from contextguard.retrieval.store import knn, upsert_chunks

    chunks = [
        _chunk("c1", "the cat sat on the mat"),
        _chunk("c2", "quarterly financial projections"),
        _chunk("c3", "a poem about the ocean"),
    ]
    upsert_chunks(engine, chunks, embedder)
    query_vec = embedder.embed(["the cat sat on the mat"])[0]
    hits = knn(engine, query_vec, k=3)
    assert hits[0].id == "c1"  # a chunk's nearest neighbour is itself


@requires_stack
def test_knn_distance_ordering(engine, embedder) -> None:
    from contextguard.retrieval.store import knn, upsert_chunks

    chunks = [_chunk(f"c{i}", t) for i, t in enumerate(["apple", "banana", "carrot"])]
    upsert_chunks(engine, chunks, embedder)
    hits = knn(engine, embedder.embed(["apple"])[0], k=3)
    distances = [h.distance for h in hits]
    assert distances == sorted(distances)


@requires_stack
def test_knn_metadata_inherited(engine, embedder) -> None:
    from contextguard.retrieval.store import knn, upsert_chunks

    upsert_chunks(engine, [_chunk("c1", "confidential acme memo")], embedder)
    hit = knn(engine, embedder.embed(["confidential acme memo"])[0], k=1)[0]
    assert hit.tenant == "acme"
    assert hit.classification == str(Classification.INTERNAL)
