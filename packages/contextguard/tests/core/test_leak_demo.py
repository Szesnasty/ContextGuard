"""The headline leak demo — the same scenario, inverted (Milestone A5).

This is the artifact the whole product narrative rests on (build plan §6a item
4): with **no policy** a naive RAG leaks a chunk that should never reach the
model; with the shipped policy on, the *same* call blocks it. Both halves run
in-memory with zero infra.

Phase-4 inversion note: the "blocked" half here is the counterpart the phase-4
library slice (`test_guard_policy.py`) already proved per-rule. This file keeps
the before/after side by side so the regression guards the *narrative*, not just
the enforcement.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from contextguard.core import ContextGuard
from contextguard_eval_harness.scenarios import (
    CONFIDENTIAL_LEAK,
    CROSS_TENANT_LEAK,
    PII_REDACTION,
    PROMPT_INJECTION,
    SCENARIOS,
    Scenario,
)

POLICY_PATH = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"

# The two scenarios whose chunk must be *dropped* entirely (vs. merely redacted).
_BLOCKING_SCENARIOS = [CROSS_TENANT_LEAK, CONFIDENTIAL_LEAK]


def _context(guard: ContextGuard, scenario: Scenario) -> str:
    result = guard.guard(scenario.user, scenario.title, list(scenario.chunks))
    return "\n".join(c.text for c in result.allowed_chunks)


@pytest.mark.parametrize("scenario", _BLOCKING_SCENARIOS, ids=lambda s: s.id)
def test_leak_reproduces_with_policy_off(scenario: Scenario) -> None:
    """Baseline (no policy): the sensitive chunk reaches the model — the leak."""
    context = _context(ContextGuard(), scenario)
    assert scenario.sensitive_marker in context  # leak confirmed


@pytest.mark.parametrize("scenario", _BLOCKING_SCENARIOS, ids=lambda s: s.id)
def test_leak_blocked_with_policy_on(scenario: Scenario) -> None:
    """Same call, policy on: the sensitive chunk never reaches the model."""
    context = _context(ContextGuard.from_policy(POLICY_PATH), scenario)
    assert scenario.sensitive_marker not in context  # leak stopped
    assert scenario.benign_marker in context  # the legitimate answer survives


@pytest.mark.parametrize("scenario", list(SCENARIOS), ids=lambda s: s.id)
def test_every_scenario_leaks_off_and_is_contained_on(scenario: Scenario) -> None:
    """All four scenarios: marker leaks with policy off, gone with policy on."""
    assert scenario.sensitive_marker in _context(ContextGuard(), scenario)
    assert scenario.sensitive_marker not in _context(
        ContextGuard.from_policy(POLICY_PATH), scenario
    )


def test_pii_chunk_is_redacted_not_dropped() -> None:
    """The PII scenario keeps the chunk (answerable) but masks the PII span."""
    guard = ContextGuard.from_policy(POLICY_PATH)
    result = guard.guard(PII_REDACTION.user, "q", list(PII_REDACTION.chunks))
    context = "\n".join(c.text for c in result.allowed_chunks)
    assert PII_REDACTION.sensitive_marker not in context
    assert "[REDACTED:EMAIL]" in context  # masked in place, chunk still present


def test_injection_chunk_is_dropped() -> None:
    """The injected document is dropped on its risk score, not silently trusted."""
    guard = ContextGuard.from_policy(POLICY_PATH)
    result = guard.guard(PROMPT_INJECTION.user, "q", list(PROMPT_INJECTION.chunks))
    kept = {c.id for c in result.allowed_chunks}
    assert "inj-sensitive" not in kept
    assert "inj-benign" in kept


def test_leak_demo_is_zero_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole before/after runs with networking disabled (ADR-010)."""

    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "socket", _boom)
    off = _context(ContextGuard(), CONFIDENTIAL_LEAK)
    on = _context(ContextGuard.from_policy(POLICY_PATH), CONFIDENTIAL_LEAK)
    assert CONFIDENTIAL_LEAK.sensitive_marker in off
    assert CONFIDENTIAL_LEAK.sensitive_marker not in on
