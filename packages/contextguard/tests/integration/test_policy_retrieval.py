"""Policy-aware retrieval push-down integration tests (Milestone B3.1).

The phase-2 leak is closed at *retrieval* time (ADR-005, line 1): the policy is
turned into tenant + classification predicates pushed into pgvector before kNN,
and the same predicate drops disallowed BM25 candidates. A `sales@acme` user
cannot reach the confidential chunk or any cross-tenant chunk *by construction* -
not filtered out afterwards.

Opt-in: needs the compose stack (Postgres + Ollama). SKIPS when down (ADR-010).
"""

from __future__ import annotations

import socket

import pytest
from contextguard.retrieval.policy_filter import build_retrieval_filter
from contextguard_contracts.enums import Classification
from contextguard_contracts.models import Chunk, UserContext
from contextguard_policy_dsl import Policy

pytestmark = pytest.mark.integration

PG_PORT = 5432
OLLAMA_PORT = 11434

POLICY = Policy.from_dict(
    {
        "version": 1,
        "default_effect": "allow",
        "roles": {"manager": {"inherits": ["sales"]}},
        "rules": [
            {
                "id": "tenant-isolation",
                "effect": "deny",
                "priority": 100,
                "when": [{"field": "chunk.tenant", "op": "neq", "ref": "user.tenant"}],
            },
            {
                "id": "sales-no-confidential",
                "effect": "deny",
                "priority": 50,
                "when": [
                    {"field": "user.roles", "op": "contains", "value": "sales"},
                    {"field": "chunk.classification", "op": "gte", "value": "confidential"},
                ],
            },
        ],
    }
)


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


def _chunk(cid: str, tenant: str, classification: Classification, text: str) -> Chunk:
    return Chunk(id=cid, doc_id=f"d-{cid}", tenant=tenant, text=text, classification=classification)


@pytest.fixture
def retriever():
    from contextguard.retrieval.bm25 import BM25Index
    from contextguard.retrieval.embeddings import get_embedder
    from contextguard.retrieval.retriever import HybridRetriever
    from contextguard.retrieval.store import all_chunks, create_schema, get_engine, upsert_chunks
    from sqlalchemy import text

    eng = get_engine()
    create_schema(eng)
    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE chunks"))

    embedder = get_embedder()
    upsert_chunks(
        eng,
        [
            _chunk("a-pub", "acme", Classification.PUBLIC, "the office coffee machine schedule"),
            _chunk(
                "a-conf",
                "acme",
                Classification.CONFIDENTIAL,
                "PROJECT FALCON: acquisition of Initech for 1.2B closes next quarter",
            ),
            _chunk(
                "c-conf",
                "contoso",
                Classification.CONFIDENTIAL,
                "contoso confidential acquisition pricing for Initech deal",
            ),
        ],
        embedder,
    )
    index = BM25Index(all_chunks(eng))
    yield HybridRetriever(eng, embedder, index)
    eng.dispose()


def _user(role: str, tenant: str = "acme") -> UserContext:
    return UserContext(sub=f"{role}@{tenant}", tenant=tenant, role=role, purpose="support")


@requires_stack
def test_sales_cannot_reach_confidential_or_cross_tenant(retriever) -> None:
    prefilter = build_retrieval_filter(POLICY, _user("sales"))
    hits = retriever.retrieve("acquisition Initech deal", k=10, prefilter=prefilter)
    ids = {h.id for h in hits}
    assert "a-conf" not in ids  # confidential, same tenant -> blocked by classification
    assert "c-conf" not in ids  # cross-tenant -> unreachable by construction
    # everything that survives is in-tenant and within the allowed classifications
    assert all(h.tenant == "acme" for h in hits)
    assert all(h.classification in ("public", "internal") for h in hits)


@requires_stack
def test_legal_reaches_confidential_but_never_cross_tenant(retriever) -> None:
    prefilter = build_retrieval_filter(POLICY, _user("legal"))
    hits = retriever.retrieve("acquisition Initech deal", k=10, prefilter=prefilter)
    ids = {h.id for h in hits}
    assert "a-conf" in ids  # legal may see confidential in its own tenant
    assert "c-conf" not in ids  # tenant isolation holds regardless of role
