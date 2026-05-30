"""Core tier: ``/v1/guard`` scan-only endpoint + isolation metric (B3.3).

The scan path needs no infra: the caller supplies the candidate chunks in the
body, so the policy-enforcing guard runs in the zero-infra core (ADR-010). These
tests prove the phase-2 leak is **inverted over HTTP** - ``sales@acme`` no longer
receives the confidential chunk and another tenant's chunk is unreachable - and
that every cross-tenant block increments
``cg_cross_tenant_attempts_blocked_total``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from contextguard.api.deps import get_scan_guard
from contextguard.core import ContextGuard
from contextguard_contracts import (
    Chunk,
    Classification,
    GuardedContext,
    Outcome,
    UserContext,
)
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

_POLICY = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"

_SALES_ACME = UserContext(sub="sales@acme", tenant="acme", role="sales", purpose="support")

_CONFIDENTIAL = Chunk(
    id="acme-conf",
    doc_id="acme-mna-falcon",
    tenant="acme",
    text="We are acquiring Initech for 1.2B.",
    classification=Classification.CONFIDENTIAL,
)
_CROSS_TENANT = Chunk(
    id="contoso-internal",
    doc_id="contoso-pricing",
    tenant="contoso",
    text="Contoso enterprise pricing is 50k/year.",
    classification=Classification.INTERNAL,
)
_PUBLIC = Chunk(
    id="acme-public",
    doc_id="acme-faq",
    tenant="acme",
    text="Our support hours are 9 to 5.",
    classification=Classification.PUBLIC,
)


def _auth(user: UserContext = _SALES_ACME) -> dict[str, str]:
    from contextguard.auth import issue_token

    return {"Authorization": f"Bearer {issue_token(user)}"}


def _use_policy_guard(client: TestClient) -> None:
    guard = ContextGuard.from_policy(_POLICY)
    client.app.dependency_overrides[get_scan_guard] = lambda: guard


def _scan(client: TestClient, chunks: list[Chunk], query: str = "what is going on?") -> Any:
    return client.post(
        "/v1/guard",
        json={"query": query, "candidate_chunks": [c.model_dump(mode="json") for c in chunks]},
        headers=_auth(),
    )


def _metric(tenant: str) -> float:
    value = REGISTRY.get_sample_value("cg_cross_tenant_attempts_blocked_total", {"tenant": tenant})
    return value or 0.0


def test_guard_blocks_confidential_for_sales(client: TestClient) -> None:
    _use_policy_guard(client)
    resp = _scan(client, [_CONFIDENTIAL, _PUBLIC])
    assert resp.status_code == 200
    guarded = GuardedContext.model_validate(resp.json())
    allowed = {c.id for c in guarded.allowed_chunks}
    assert "acme-conf" not in allowed
    assert "acme-public" in allowed
    decision = next(d for d in guarded.decisions if d.chunk_id == "acme-conf")
    assert decision.outcome == Outcome.BLOCKED
    assert "sales-no-confidential" in decision.policies_triggered


def test_guard_blocks_cross_tenant_and_counts_metric(client: TestClient) -> None:
    _use_policy_guard(client)
    before = _metric("acme")
    resp = _scan(client, [_CROSS_TENANT, _PUBLIC])
    assert resp.status_code == 200
    guarded = GuardedContext.model_validate(resp.json())
    allowed = {c.id for c in guarded.allowed_chunks}
    assert "contoso-internal" not in allowed
    assert "acme-public" in allowed
    decision = next(d for d in guarded.decisions if d.chunk_id == "contoso-internal")
    assert decision.outcome == Outcome.BLOCKED
    assert "tenant-isolation" in decision.policies_triggered
    assert _metric("acme") == before + 1.0


def test_guard_same_tenant_block_does_not_count_cross_tenant(client: TestClient) -> None:
    _use_policy_guard(client)
    before = _metric("acme")
    # The confidential block is same-tenant: it must NOT touch the cross-tenant
    # counter, which is specifically the isolation proof.
    _scan(client, [_CONFIDENTIAL])
    assert _metric("acme") == before


def test_guard_is_scan_only_no_answer(client: TestClient) -> None:
    _use_policy_guard(client)
    resp = _scan(client, [_PUBLIC])
    assert resp.status_code == 200
    # The response is a GuardedContext, not a QueryResponse: no model was called.
    assert "answer" not in resp.json()


def test_guard_requires_auth(client: TestClient) -> None:
    _use_policy_guard(client)
    resp = client.post(
        "/v1/guard",
        json={"query": "hi", "candidate_chunks": [_PUBLIC.model_dump(mode="json")]},
    )
    assert resp.status_code in (401, 403)


def test_metrics_endpoint_exposes_isolation_counter(client: TestClient) -> None:
    _use_policy_guard(client)
    _scan(client, [_CROSS_TENANT])
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "cg_cross_tenant_attempts_blocked_total" in resp.text
