"""Postgres JSONB evidence sink: persist, replay, query (Milestone B4.2).

Opt-in: requires Postgres from the compose stack (`make up`). SKIPS when the DB
port is closed so `make test` stays green offline (ADR-010). Needs only Postgres
(no Ollama), so it has its own narrower guard than the pgvector store tests.

    make up && uv run pytest packages/contextguard/tests/integration -m integration
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from contextguard.core import ContextGuard
from contextguard.core.types import Chunk, Classification, UserContext

pytestmark = pytest.mark.integration

PG_PORT = 5432
_EXAMPLE_POLICY = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


requires_pg = pytest.mark.skipif(
    not _port_open("localhost", PG_PORT),
    reason="local Postgres not running (run `make up`)",
)


def _sales() -> UserContext:
    return UserContext(sub="sales@acme", tenant="acme", role="sales", purpose="support")


def _confidential_chunk() -> Chunk:
    return Chunk(
        id="conf-1",
        doc_id="mna",
        tenant="acme",
        text="Project Falcon acquires Initech for 1.2B.",
        classification=Classification.CONFIDENTIAL,
    )


@pytest.fixture
def sink():
    from contextguard.db.evidence import PostgresEvidenceSink, create_evidence_schema
    from contextguard.retrieval.store import get_engine

    eng = get_engine()
    create_evidence_schema(eng)
    from sqlalchemy import text

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE evidence"))
    yield PostgresEvidenceSink(eng)
    eng.dispose()


@requires_pg
def test_emit_then_replay_round_trips_record(sink) -> None:
    guard = ContextGuard.from_policy(_EXAMPLE_POLICY, sink=sink)
    guard.guard(_sales(), "are we acquiring anyone?", [_confidential_chunk()])

    emitted = sink.last_evidence()
    assert emitted is not None
    query_id = emitted["query_id"]
    replayed = sink.replay(query_id)
    assert replayed == emitted  # the stored record reproduces exactly


@requires_pg
def test_replay_unknown_id_returns_none(sink) -> None:
    assert sink.replay("does-not-exist") is None


@requires_pg
def test_blocked_confidential_record_is_queryable_by_policy(sink) -> None:
    guard = ContextGuard.from_policy(_EXAMPLE_POLICY, sink=sink)
    guard.guard(_sales(), "are we acquiring anyone?", [_confidential_chunk()])

    # sales cannot see confidential -> sales-no-confidential fired.
    by_policy = sink.query_by_policy("sales-no-confidential")
    assert len(by_policy) == 1
    assert by_policy[0]["policies_triggered"] == ["sales-no-confidential"]

    by_tenant = sink.query_by_tenant("acme")
    assert len(by_tenant) == 1
    assert sink.query_by_tenant("contoso") == []


@requires_pg
def test_emit_is_idempotent_on_query_id(sink) -> None:
    from datetime import UTC, datetime

    from contextguard.core.types import EvidenceMetrics, EvidenceRecord

    record = EvidenceRecord(
        query_id="fixed-id",
        user=_sales(),
        query="hi",
        decisions=[],
        metrics=EvidenceMetrics(),
        policies_triggered=[],
        created_at=datetime.now(UTC),
    )
    sink.emit(record)
    sink.emit(record)  # second emit must update, not duplicate
    assert len(sink.query_by_tenant("acme")) == 1
