"""guard() policy enforcement tests (Milestone A3 — library slice of phase 4).

The leak from the baseline (a `sales@acme` user receiving a confidential chunk,
or a cross-tenant chunk) is now *blocked* at mid-retrieval — proven here with no
infra, no DB, no network.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from contextguard.core import ContextGuard
from contextguard.core.types import Chunk, Classification, Outcome, UserContext
from contextguard_eval_harness.strategies import chunk_lists, user_contexts
from hypothesis import HealthCheck, given, settings

POLICY_PATH = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"


def _sales_acme() -> UserContext:
    return UserContext(sub="u1", tenant="acme", role="sales", purpose="support")


def _chunk(cid: str, tenant: str, classification: Classification) -> Chunk:
    return Chunk(
        id=cid,
        doc_id="d1",
        tenant=tenant,
        text=f"content for {cid}",
        classification=classification,
    )


def _guard() -> ContextGuard:
    return ContextGuard.from_policy(POLICY_PATH)


def test_example_policy_file_exists() -> None:
    assert POLICY_PATH.exists(), POLICY_PATH


def test_confidential_blocked_for_sales() -> None:
    chunks = [
        _chunk("public", "acme", Classification.PUBLIC),
        _chunk("secret", "acme", Classification.CONFIDENTIAL),
    ]
    result = _guard().guard(_sales_acme(), "q", chunks)
    allowed = {c.id for c in result.allowed_chunks}
    assert "public" in allowed
    assert "secret" not in allowed
    blocked = {d.chunk_id: d for d in result.decisions if d.outcome == Outcome.BLOCKED}
    assert "secret" in blocked
    assert blocked["secret"].policies_triggered == ["sales-no-confidential"]


def test_cross_tenant_blocked() -> None:
    chunks = [_chunk("foreign", "contoso", Classification.PUBLIC)]
    result = _guard().guard(_sales_acme(), "q", chunks)
    assert result.allowed_chunks == []
    assert result.decisions[0].outcome == Outcome.BLOCKED
    assert result.decisions[0].policies_triggered == ["tenant-isolation"]


def test_allowed_chunk_passes() -> None:
    chunks = [_chunk("ok", "acme", Classification.INTERNAL)]
    result = _guard().guard(_sales_acme(), "q", chunks)
    assert [c.id for c in result.allowed_chunks] == ["ok"]
    assert result.decisions[0].outcome == Outcome.ALLOWED


def test_tokens_drop_when_chunks_blocked() -> None:
    chunks = [
        _chunk("public", "acme", Classification.PUBLIC),
        _chunk("secret", "acme", Classification.CONFIDENTIAL),
    ]
    result = _guard().guard(_sales_acme(), "q", chunks)
    assert result.tokens_after < result.tokens_before


def test_evidence_records_triggered_policies() -> None:
    chunks = [
        _chunk("foreign", "contoso", Classification.PUBLIC),
        _chunk("secret", "acme", Classification.RESTRICTED),
    ]
    guard = _guard()
    guard.guard(_sales_acme(), "q", chunks)
    ev = guard.last_evidence()
    assert ev is not None
    assert set(ev["policies_triggered"]) == {"tenant-isolation", "sales-no-confidential"}
    assert ev["metrics"]["chunks_blocked"] == 2


def test_enforcement_is_zero_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "socket", _boom)
    chunks = [_chunk("secret", "acme", Classification.CONFIDENTIAL)]
    result = _guard().guard(_sales_acme(), "q", chunks)
    assert result.allowed_chunks == []


def test_no_policy_is_passthrough() -> None:
    chunks = [_chunk("secret", "acme", Classification.CONFIDENTIAL)]
    result = ContextGuard().guard(_sales_acme(), "q", chunks)
    assert len(result.allowed_chunks) == 1


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(user=user_contexts(), chunks=chunk_lists())
def test_policy_enforcement_deterministic(user: UserContext, chunks: list[Chunk]) -> None:
    guard = _guard()
    assert guard.guard(user, "q", chunks) == guard.guard(user, "q", chunks)


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(user=user_contexts(), chunks=chunk_lists())
def test_fail_closed_blocked_never_allowed(user: UserContext, chunks: list[Chunk]) -> None:
    result = _guard().guard(user, "q", chunks)
    allowed_ids = {c.id for c in result.allowed_chunks}
    for d in result.decisions:
        if d.outcome == Outcome.BLOCKED:
            assert d.chunk_id not in allowed_ids
