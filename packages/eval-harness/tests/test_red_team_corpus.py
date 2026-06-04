"""Red-team corpus-shape tests.

These assert the declarative red-team corpus is well-formed and that each case is
a genuine attack carrying a golden decision. Pure, zero-infra: they read files
and parse YAML, nothing heavier.
"""

from __future__ import annotations

from contextguard_contracts import Chunk, Outcome, UserContext
from contextguard_eval_harness.red_team import (
    RED_TEAM_DIR,
    ChunkExpectation,
    RedTeamCase,
    load_red_team_corpus,
)


def test_corpus_loads() -> None:
    cases = load_red_team_corpus()
    assert len(cases) >= 6
    assert all(isinstance(c, RedTeamCase) for c in cases)


def test_at_least_five_attack_classes() -> None:
    classes = {c.attack_class for c in load_red_team_corpus()}
    assert len(classes) >= 5, f"expected >= 5 attack classes, got {sorted(classes)}"


def test_every_case_is_a_genuine_attack() -> None:
    """Each case carries a valid user, >= 1 chunk, and >= 1 non-allowed verdict."""
    for case in load_red_team_corpus():
        assert isinstance(case.user, UserContext)
        assert case.chunks and all(isinstance(ch, Chunk) for ch in case.chunks)
        assert case.attack_chunk_ids, f"{case.id} stops nothing"
        assert case.sensitive_marker
        assert case.benign_marker


def test_expectations_cover_every_chunk() -> None:
    for case in load_red_team_corpus():
        chunk_ids = {ch.id for ch in case.chunks}
        assert set(case.expectations) == chunk_ids, f"{case.id} expectation/chunk mismatch"


def test_named_rules_are_non_empty_strings() -> None:
    for case in load_red_team_corpus():
        for exp in case.expectations.values():
            assert isinstance(exp, ChunkExpectation)
            if exp.rule is not None:
                assert exp.rule.strip(), "expect.rule must be a non-empty string"
            # redacted_types only make sense for a redacted verdict.
            if exp.redacted_types:
                assert exp.outcome is Outcome.REDACTED


def test_loader_is_deterministic() -> None:
    first = load_red_team_corpus()
    second = load_red_team_corpus()
    assert [c.id for c in first] == [c.id for c in second]


def test_corpus_dir_holds_yaml_files() -> None:
    assert RED_TEAM_DIR.is_dir()
    assert list(RED_TEAM_DIR.glob("*.yaml")), "no red-team corpora found"
