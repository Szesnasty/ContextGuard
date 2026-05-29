"""The benchmark is a passing, reproducible artifact (Milestone A5)."""

from __future__ import annotations

from contextguard_eval_harness.benchmark import render_markdown, run_benchmark
from contextguard_eval_harness.scenarios import SCENARIOS


def test_every_scenario_leaks_off_and_is_contained_on() -> None:
    report = run_benchmark()
    assert report.total == len(SCENARIOS) == 4
    assert report.leak_rate_off == 1.0  # naive RAG leaks every scenario
    assert report.leak_rate_on == 0.0  # the firewall stops all of them
    assert report.block_rate == 1.0
    assert report.false_positive_rate == 0.0  # no legitimate chunk lost


def test_benchmark_is_deterministic() -> None:
    assert render_markdown(run_benchmark()) == render_markdown(run_benchmark())


def test_rendered_markdown_lists_all_scenarios() -> None:
    md = render_markdown(run_benchmark())
    for scenario in SCENARIOS:
        assert scenario.title in md
    assert "Leak rate" in md
