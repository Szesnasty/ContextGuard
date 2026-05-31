"""Core tier: ``cg_*`` product metrics on ``/metrics`` (B4.3, Phase 5 step 6).

Every guarded query (via ``/v1/guard`` here, the zero-infra scan path) emits the
ADR-003 product metrics: how many chunks were retrieved, allowed, blocked (by
reason), redacted (by type), the token minimization histograms, the guard SLO
latency, and one evidence record. ``cg_replay_mismatch_total`` is the determinism
alarm whose healthy value is ``0`` (DoD#7).

These assert *deltas* against the shared default registry so they compose with
the other adapter tests that also scrape it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from contextguard.api.deps import get_scan_guard
from contextguard.api.metrics import record_replay_mismatch
from contextguard.core import ContextGuard
from contextguard.core.evidence_jsonl import replay_matches
from contextguard_contracts import Chunk, Classification, UserContext
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
_PUBLIC = Chunk(
    id="acme-public",
    doc_id="acme-faq",
    tenant="acme",
    text="Our support hours are 9 to 5.",
    classification=Classification.PUBLIC,
)
_SECRET = Chunk(
    id="acme-secret",
    doc_id="acme-runbook",
    tenant="acme",
    text="Deploy with key AKIAIOSFODNN7EXAMPLE to the prod bucket.",
    classification=Classification.INTERNAL,
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


def _value(name: str, labels: dict[str, str] | None = None) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_scan_emits_core_counters(client: TestClient) -> None:
    _use_policy_guard(client)
    retrieved = _value("cg_chunks_retrieved_total")
    allowed = _value("cg_chunks_allowed_total")
    blocked = _value("cg_chunks_blocked_total", {"reason": "rule:sales-no-confidential"})
    redacted = _value("cg_chunks_redacted_total", {"type": "secret"})
    records = _value("cg_evidence_records_total")

    resp = _scan(client, [_CONFIDENTIAL, _PUBLIC, _SECRET])
    assert resp.status_code == 200

    assert _value("cg_chunks_retrieved_total") == retrieved + 3.0
    assert _value("cg_chunks_allowed_total") == allowed + 1.0
    assert (
        _value("cg_chunks_blocked_total", {"reason": "rule:sales-no-confidential"}) == blocked + 1.0
    )
    assert _value("cg_chunks_redacted_total", {"type": "secret"}) == redacted + 1.0
    assert _value("cg_evidence_records_total") == records + 1.0


def test_token_minimization_histograms_observed(client: TestClient) -> None:
    _use_policy_guard(client)
    before_count = _value("cg_tokens_before_count")
    after_count = _value("cg_tokens_after_count")
    latency_count = _value("cg_guard_total_latency_ms_count")
    before_sum = _value("cg_tokens_before_sum")
    after_sum = _value("cg_tokens_after_sum")

    # Blocking the confidential chunk removes tokens: before > after for this query.
    _scan(client, [_CONFIDENTIAL, _PUBLIC])

    assert _value("cg_tokens_before_count") == before_count + 1.0
    assert _value("cg_tokens_after_count") == after_count + 1.0
    assert _value("cg_guard_total_latency_ms_count") == latency_count + 1.0
    # Minimization: the firewall dropped tokens, so before grew by more than after.
    assert _value("cg_tokens_before_sum") - before_sum > _value("cg_tokens_after_sum") - after_sum


def test_metrics_endpoint_exposes_product_family(client: TestClient) -> None:
    _use_policy_guard(client)
    _scan(client, [_CONFIDENTIAL, _PUBLIC, _SECRET])
    body = client.get("/metrics").text
    for name in (
        "cg_chunks_retrieved_total",
        "cg_chunks_allowed_total",
        "cg_chunks_blocked_total",
        "cg_chunks_redacted_total",
        "cg_tokens_before_bucket",
        "cg_tokens_after_bucket",
        "cg_guard_total_latency_ms_bucket",
        "cg_evidence_records_total",
        "cg_replay_mismatch_total",
    ):
        assert name in body


def test_replay_of_same_input_keeps_mismatch_zero() -> None:
    before = _value("cg_replay_mismatch_total")
    # Two independent guards, same policy + same input: the decision view must
    # be identical (only query_id/created_at differ), so no mismatch is recorded.
    first = ContextGuard.from_policy(_POLICY)
    second = ContextGuard.from_policy(_POLICY)
    first.guard(_SALES_ACME, "q", [_CONFIDENTIAL, _PUBLIC])
    second.guard(_SALES_ACME, "q", [_CONFIDENTIAL, _PUBLIC])
    record_a = first.last_evidence()
    record_b = second.last_evidence()
    assert record_a is not None
    assert record_b is not None

    matched = replay_matches(record_a, record_b)
    assert matched is True
    record_replay_mismatch(mismatch=not matched)

    assert _value("cg_replay_mismatch_total") == before


def test_record_replay_mismatch_increments_on_divergence() -> None:
    before = _value("cg_replay_mismatch_total")
    record_replay_mismatch(mismatch=True)
    assert _value("cg_replay_mismatch_total") == before + 1.0
