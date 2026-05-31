"""Run the red-team corpus through the firewall and render ``RED-TEAM.md`` (B5.2).

The runner drives every :class:`~contextguard_eval_harness.red_team.RedTeamCase`
through the **in-memory** ``ContextGuard.from_policy`` and grades it two ways:

1. **Structured decision** — the actual per-chunk ``outcome`` (and, when the case
   names one, the rule that fired) must equal the golden ``expect``. This catches
   "blocked for the wrong reason" and "redacted instead of blocked", which a bare
   marker check cannot.
2. **Marker check** — the case's ``sensitive_marker`` must not survive into the
   assembled context, while the ``benign_marker`` must (the false-positive guard).

Grading is a deterministic, mechanical check — **no LLM-as-judge** — so
``RED-TEAM.md`` is reproducible and byte-stable. Zero-infra: no Docker, no
network, no models.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from contextguard_contracts import Chunk, ChunkDecision, Outcome

from contextguard import ContextGuard
from contextguard_eval_harness.red_team import (
    RED_TEAM_DIR,
    ChunkExpectation,
    RedTeamCase,
    load_red_team_corpus,
)

DEFAULT_POLICY = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"


@dataclass(frozen=True)
class ChunkOutcome:
    """The graded comparison of one chunk's actual verdict against its golden one."""

    chunk_id: str
    expected: ChunkExpectation
    actual_outcome: Outcome
    actual_rule: str | None
    ok: bool


@dataclass(frozen=True)
class CaseResult:
    """The graded outcome of one red-team case."""

    case: RedTeamCase
    chunk_outcomes: list[ChunkOutcome]
    leak_contained: bool
    false_positive: bool

    @property
    def passed(self) -> bool:
        """True when every chunk met its expectation, the leak was contained, and
        no benign chunk was lost."""
        return (
            all(co.ok for co in self.chunk_outcomes)
            and self.leak_contained
            and not self.false_positive
        )


@dataclass(frozen=True)
class RedTeamReport:
    """Aggregate metrics over every red-team case."""

    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self._rate([r.passed for r in self.results])

    @property
    def leak_rate(self) -> float:
        """Fraction of cases whose sensitive marker survived into the context."""
        return self._rate([not r.leak_contained for r in self.results])

    @property
    def false_positive_rate(self) -> float:
        return self._rate([r.false_positive for r in self.results])

    def by_attack_class(self) -> dict[str, tuple[int, int]]:
        """Map attack class → (passed, total), in first-seen order."""
        buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in self.results:
            bucket = buckets[r.case.attack_class]
            bucket[1] += 1
            if r.passed:
                bucket[0] += 1
        return {k: (v[0], v[1]) for k, v in buckets.items()}

    def _rate(self, flags: list[bool]) -> float:
        if not self.results:
            return 0.0
        return round(sum(1 for f in flags if f) / self.total, 4)


def _redacted_types(chunk: Chunk | None) -> set[str]:
    """The sensitivity types a guarded (masked) chunk carried, from its spans."""
    if chunk is None:
        return set()
    types: set[str] = set()
    if chunk.pii_spans:
        types.add("pii")
    if chunk.secret_spans:
        types.add("secret")
    return types


def _grade_chunk(
    expected: ChunkExpectation, decision: ChunkDecision, allowed: dict[str, Chunk]
) -> ChunkOutcome:
    rule = decision.policies_triggered[0] if decision.policies_triggered else None
    ok = decision.outcome is expected.outcome
    if ok and expected.rule is not None:
        ok = rule == expected.rule
    if ok and expected.redacted_types:
        ok = set(expected.redacted_types).issubset(_redacted_types(allowed.get(decision.chunk_id)))
    return ChunkOutcome(
        chunk_id=decision.chunk_id,
        expected=expected,
        actual_outcome=decision.outcome,
        actual_rule=rule,
        ok=ok,
    )


def run_case(case: RedTeamCase, *, guard: ContextGuard) -> CaseResult:
    """Run one case through ``guard`` and grade it against its golden decisions."""
    guarded = guard.guard(case.user, case.query, list(case.chunks))
    allowed = {chunk.id: chunk for chunk in guarded.allowed_chunks}
    context = "\n".join(chunk.text for chunk in guarded.allowed_chunks)
    chunk_outcomes = [
        _grade_chunk(case.expectations[d.chunk_id], d, allowed)
        for d in guarded.decisions
        if d.chunk_id in case.expectations
    ]
    return CaseResult(
        case=case,
        chunk_outcomes=chunk_outcomes,
        leak_contained=case.sensitive_marker not in context,
        false_positive=case.benign_marker not in context,
    )


def run_red_team(
    corpus_root: Path = RED_TEAM_DIR, *, policy_path: str | Path = DEFAULT_POLICY
) -> RedTeamReport:
    """Run every case under ``corpus_root`` against the policy and grade them."""
    guard = ContextGuard.from_policy(policy_path)
    cases = load_red_team_corpus(corpus_root)
    return RedTeamReport(results=[run_case(c, guard=guard) for c in cases])


def _check(flag: bool) -> str:
    return "✅" if flag else "❌"


def render_markdown(
    report: RedTeamReport,
    *,
    policy_path: str | Path = DEFAULT_POLICY,
    replay_mismatches: int | None = None,
) -> str:
    """Render ``report`` as the committed ``RED-TEAM.md`` artifact.

    When ``replay_mismatches`` is supplied (the B5.3 determinism sweep), it is
    surfaced as the ``cg_replay_mismatch_total`` audit line.
    """
    policy_name = Path(policy_path).name
    lines: list[str] = [
        "# ContextGuard — red-team benchmark",
        "",
        "> Generated by `make red-team` "
        "(`python -m contextguard_eval_harness.red_team_runner`). Do not edit by hand.",
        "",
        "Every case in `data/red-team-corpora/` is run through "
        f"`ContextGuard.from_policy(data/policies/{policy_name})`. Each chunk's "
        "actual verdict is graded against its **golden decision** (`expect`), and "
        "the case's sensitive marker must not survive into the assembled context "
        "while the benign marker must. Grading is a deterministic check — no "
        "LLM-as-judge.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases | {report.total} |",
        f"| Pass rate | {report.pass_rate:.0%} |",
        f"| Leak rate | {report.leak_rate:.0%} |",
        f"| False-positive rate | {report.false_positive_rate:.0%} |",
    ]
    if replay_mismatches is not None:
        lines.append(f"| `cg_replay_mismatch_total` | {replay_mismatches} |")
    lines += [
        "",
        "## By attack class",
        "",
        "| Attack class | Passed |",
        "|---|---|",
    ]
    for attack_class, (passed, total) in report.by_attack_class().items():
        lines.append(f"| {attack_class} | {_check(passed == total)} {passed}/{total} |")
    lines += [
        "",
        "## Cases",
        "",
        "| Case | Attack class | Expected → actual | Leak contained | No false positive | Pass |",
        "|---|---|---|---|---|---|",
    ]
    for r in report.results:
        verdicts = "; ".join(
            f"`{co.chunk_id}` {co.expected.outcome.value}"
            f"{'' if co.expected.rule is None else f' ({co.expected.rule})'}"
            f" → {_check(co.ok)} {co.actual_outcome.value}"
            for co in r.chunk_outcomes
        )
        lines.append(
            f"| {r.case.title} | {r.case.attack_class} | {verdicts} "
            f"| {_check(r.leak_contained)} | {_check(not r.false_positive)} "
            f"| {_check(r.passed)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """CLI entry point: regenerate ``RED-TEAM.md`` at the repo root."""
    from contextguard_eval_harness.determinism import run_determinism

    report = run_red_team()
    determinism = run_determinism()
    out = DEFAULT_POLICY.parents[2] / "RED-TEAM.md"  # repo root
    out.write_text(
        render_markdown(report, replay_mismatches=determinism.mismatches) + "\n", encoding="utf-8"
    )
    print(
        f"red-team: wrote {out} ({report.total} cases, pass {report.pass_rate:.0%}, "
        f"leak {report.leak_rate:.0%}, false-positive {report.false_positive_rate:.0%}, "
        f"replay-mismatches {determinism.mismatches})"
    )


if __name__ == "__main__":
    main()


__all__ = [
    "CaseResult",
    "ChunkOutcome",
    "RedTeamReport",
    "main",
    "render_markdown",
    "run_case",
    "run_red_team",
]
