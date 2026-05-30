"""Ingestion job integration tests (Milestone B2.2).

Opt-in: these need the compose stack (Postgres + Redis + Ollama) and the
``[ingest]`` / ``[pgvector]`` / ``[embeddings]`` extras. They SKIP when the stack
is down so ``make test`` stays green offline (ADR-010).

    make up && uv run pytest packages/contextguard/tests/integration -m integration
"""

from __future__ import annotations

import socket

import pytest
from contextguard_contracts.enums import Classification
from contextguard_contracts.models import Chunk

pytestmark = pytest.mark.integration

PG_PORT = 5432
REDIS_PORT = 6379
OLLAMA_PORT = 11434


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


requires_stack = pytest.mark.skipif(
    not (
        _port_open("localhost", PG_PORT)
        and _port_open("localhost", REDIS_PORT)
        and _port_open("localhost", OLLAMA_PORT)
    ),
    reason="local compose stack not running (run `make up`)",
)


def _chunk(
    chunk_id: str, text: str, *, classification: Classification = Classification.INTERNAL
) -> Chunk:
    return Chunk(
        id=chunk_id,
        doc_id="doc-1",
        tenant="acme",
        text=text,
        classification=classification,
    )


@pytest.fixture
def engine():
    from contextguard.retrieval.store import create_schema, get_engine
    from sqlalchemy import text

    eng = get_engine()
    create_schema(eng)
    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE chunks"))
    yield eng
    eng.dispose()


@requires_stack
def test_ingest_chunks_enriches_and_persists(engine) -> None:
    """The job body enriches + embeds + lands chunks with queryable scalars."""
    from contextguard.jobs.ingest import ingest_chunks
    from sqlalchemy import text

    chunks = [
        _chunk("c1", "contact jane.doe@example.com about the invoice"),
        _chunk("c2", "the quarterly weather summary"),
    ]
    report = ingest_chunks(chunks, engine=engine)

    assert report.chunks_written == 2
    assert report.by_classification.get(str(Classification.INTERNAL)) == 2
    with engine.connect() as conn:
        pii = conn.execute(text("SELECT pii_count FROM chunks WHERE id = 'c1'")).scalar_one()
    assert pii >= 1  # the email was detected during ingestion, not at query time


@requires_stack
def test_enqueue_then_worker_drains(engine) -> None:
    """The full RQ path: enqueue on Redis, a burst worker processes it (B2.2 DoD)."""
    from contextguard.jobs.ingest import enqueue_ingest
    from contextguard.jobs.worker import get_connection, run_worker
    from sqlalchemy import text

    connection = get_connection()
    # Isolate from any other run: clear the ingest queue first.
    from rq import Queue

    Queue("ingest", connection=connection).empty()

    chunks = [_chunk("q1", "the acme acquisition memo mentions Initech")]
    job = enqueue_ingest(chunks, connection=connection)
    assert job.get_status() in {"queued", "started", "deferred"}

    run_worker(burst=True)

    job.refresh()
    assert job.get_status() == "finished"
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM chunks WHERE id = 'q1'")).scalar_one()
    assert count == 1
