"""Tests for the replay-determinism sweep (B5.3)."""

from __future__ import annotations

from contextguard_eval_harness.determinism import (
    DeterminismReport,
    run_determinism,
)
from contextguard_eval_harness.red_team import load_red_team_corpus
from contextguard_eval_harness.red_team_runner import DEFAULT_POLICY
from contextguard_eval_harness.scenarios import SCENARIOS

from contextguard import ContextGuard


def test_corpus_is_fully_deterministic() -> None:
    report = run_determinism()
    assert isinstance(report, DeterminismReport)
    assert report.mismatches == 0
    assert report.passed
    assert all(r.matched for r in report.results)


def test_sweep_covers_red_team_and_scenarios() -> None:
    report = run_determinism()
    assert report.total == len(load_red_team_corpus()) + len(SCENARIOS)


class _NonDeterministicGuard(ContextGuard):
    """A guard whose evidence flips between runs — the harness must catch it."""

    _toggle = False

    def last_evidence(self) -> dict[str, object] | None:
        type(self)._toggle = not type(self)._toggle
        return {"decisions": [type(self)._toggle], "query_id": "x", "created_at": "y"}


def test_injected_nondeterminism_is_detected() -> None:
    report = run_determinism(guard_factory=lambda: _NonDeterministicGuard())
    assert report.mismatches > 0
    assert not report.passed


def test_record_replay_mismatch_called_per_case(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        "contextguard_eval_harness.determinism._record_replay_mismatch",
        lambda *, mismatch: calls.append(mismatch),
    )
    report = run_determinism()
    assert len(calls) == report.total
    assert calls == [False] * report.total


def test_guard_factory_builds_fresh_guards() -> None:
    # A factory that records each construction proves two guards per case.
    built: list[int] = []

    def factory() -> ContextGuard:
        built.append(1)
        return ContextGuard.from_policy(DEFAULT_POLICY)

    report = run_determinism(guard_factory=factory)
    assert len(built) == 2 * report.total
