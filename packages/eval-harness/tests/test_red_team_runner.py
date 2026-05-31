"""Tests for the red-team runner (B5.2) — structured grading over the live guard."""

from __future__ import annotations

from dataclasses import replace

from contextguard_contracts import Outcome
from contextguard_eval_harness.red_team import load_red_team_corpus
from contextguard_eval_harness.red_team_runner import (
    DEFAULT_POLICY,
    RedTeamReport,
    render_markdown,
    run_case,
    run_red_team,
)

from contextguard import ContextGuard


def test_corpus_fully_defended() -> None:
    report = run_red_team()
    assert report.total >= 6
    assert report.pass_rate == 1.0
    assert report.leak_rate == 0.0
    assert report.false_positive_rate == 0.0
    assert all(r.passed for r in report.results)


def test_every_case_contains_leak_and_keeps_benign() -> None:
    report = run_red_team()
    for r in report.results:
        assert r.leak_contained, f"{r.case.id}: sensitive marker survived"
        assert not r.false_positive, f"{r.case.id}: benign marker dropped"


def test_actual_rule_matches_named_golden_rule() -> None:
    report = run_red_team()
    for r in report.results:
        for co in r.chunk_outcomes:
            if co.expected.rule is not None:
                assert co.actual_rule == co.expected.rule
                assert co.ok


def test_by_attack_class_all_green() -> None:
    report = run_red_team()
    by_class = report.by_attack_class()
    assert len(by_class) >= 5
    for passed, total in by_class.values():
        assert passed == total


def test_wrong_golden_label_fails_the_case() -> None:
    # Corrupt one expectation: claim a blocked chunk should have been allowed.
    cases = load_red_team_corpus()
    guard = ContextGuard.from_policy(DEFAULT_POLICY)
    target = next(
        c for c in cases if any(e.outcome is Outcome.BLOCKED for e in c.expectations.values())
    )
    bad_id = next(cid for cid, e in target.expectations.items() if e.outcome is Outcome.BLOCKED)
    corrupted = replace(
        target,
        expectations={
            **target.expectations,
            bad_id: replace(target.expectations[bad_id], outcome=Outcome.ALLOWED, rule=None),
        },
    )
    result = run_case(corrupted, guard=guard)
    assert not result.passed


def test_render_markdown_is_deterministic() -> None:
    report = run_red_team()
    assert render_markdown(report) == render_markdown(report)


def test_render_markdown_has_expected_sections() -> None:
    md = render_markdown(run_red_team())
    assert "# ContextGuard — red-team benchmark" in md
    assert "## Summary" in md
    assert "## By attack class" in md
    assert "## Cases" in md
    assert "| Pass rate | 100% |" in md


def test_report_total_matches_corpus() -> None:
    report = run_red_team()
    assert isinstance(report, RedTeamReport)
    assert report.total == len(load_red_team_corpus())
