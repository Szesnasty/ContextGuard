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


@requires_stack
def test_enrichment_scalars_persisted(engine, embedder) -> None:
    """The ingestion worker's enrichment lands as queryable SQL columns (B2.1)."""
    from contextguard.retrieval.store import upsert_chunks
    from contextguard.risk import enrich
    from sqlalchemy import text

    pii_chunk = enrich(_chunk("c1", "contact jane.doe@example.com for details"))
    clean_chunk = enrich(_chunk("c2", "the quarterly report is ready"))
    written = upsert_chunks(engine, [pii_chunk, clean_chunk], embedder)
    assert written == 2

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT pii_count, secret_count, risk_score FROM chunks WHERE id = 'c1'")
        ).one()
    pii_count, secret_count, risk = row
    # The PII chunk carries a detected email; nothing is NULL.
    assert pii_count >= 1
    assert secret_count == 0
    assert risk is not None


@requires_stack
def test_classification_distribution(engine, embedder) -> None:
    from contextguard.retrieval.store import classification_distribution, upsert_chunks

    chunks = [
        _chunk("pub", "public notice"),
        Chunk(
            id="conf",
            doc_id="doc-2",
            tenant="acme",
            text="confidential acquisition memo",
            classification=Classification.CONFIDENTIAL,
        ),
    ]
    upsert_chunks(engine, chunks, embedder)
    dist = classification_distribution(engine)
    assert dist.get(str(Classification.INTERNAL)) == 1
    assert dist.get(str(Classification.CONFIDENTIAL)) == 1


@requires_stack
def test_enrichment_summary(engine, embedder) -> None:
    from contextguard.retrieval.store import enrichment_summary, upsert_chunks
    from contextguard.risk import enrich

    chunks = [
        enrich(_chunk("c1", "contact jane.doe@example.com about the invoice")),
        enrich(_chunk("c2", "the weather is sunny today")),
    ]
    upsert_chunks(engine, chunks, embedder)
    summary = enrichment_summary(engine)
    assert summary.chunks == 2
    assert summary.chunks_with_pii >= 1
    assert summary.max_risk_score >= 0.0
