"""Replay-determinism sweep over the whole corpus (B5.3).

The product's audit claim — *"replay reproduces the stored decision"* — is only
credible if it holds across the *entire* corpus, not one unit test. A single
non-deterministic dependency reaching core (set iteration order, a dict ordering,
a clock leak into a decision) would silently corrupt the evidence trail.

This harness promotes the B4.3 test-level invariant into a corpus-wide gate: for
every case it guards the same input **twice** with a fresh
``ContextGuard.from_policy`` and asserts that the two evidence records share the
same *decision view* (volatile ``query_id`` / ``created_at`` dropped) via
:func:`~contextguard.core.evidence_jsonl.replay_matches`. Each comparison also
exercises the live ``cg_replay_mismatch_total`` counter through
:func:`~contextguard.api.metrics.record_replay_mismatch`.

Cases = the red-team corpus (B5.1) plus the A5 benchmark ``SCENARIOS``. Zero-infra:
in-memory guard only - the Postgres replay round-trip is covered by B4.2.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from contextguard.core.evidence_jsonl import replay_matches
from contextguard_contracts import Chunk, UserContext

from contextguard import ContextGuard
from contextguard_eval_harness.red_team import load_red_team_corpus
from contextguard_eval_harness.red_team_runner import DEFAULT_POLICY
from contextguard_eval_harness.scenarios import SCENARIOS

# Imported lazily-safe: record_replay_mismatch lives in the [api] tier (it touches
# prometheus_client). The sweep itself is zero-infra, so we only reach for it when
# available and degrade to a no-op otherwise (keeps `make red-team` runnable with
# just the core installed).
try:  # pragma: no cover - import guard
    from contextguard.api.metrics import record_replay_mismatch as _record_replay_mismatch
except ModuleNotFoundError:  # pragma: no cover - core-only install

    def _record_replay_mismatch(*, mismatch: bool) -> None:
        return None


@dataclass(frozen=True)
class _Case:
    """A normalized (id, user, query, chunks) view over both corpus sources."""

    id: str
    user: UserContext
    query: str
    chunks: list[Chunk]


@dataclass(frozen=True)
class DeterminismResult:
    """The replay outcome for one case."""

    case_id: str
    matched: bool


@dataclass(frozen=True)
class DeterminismReport:
    """Aggregate replay-determinism outcome over the whole corpus."""

    results: list[DeterminismResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def mismatches(self) -> int:
        return sum(1 for r in self.results if not r.matched)

    @property
    def passed(self) -> bool:
        return self.mismatches == 0


def _collect_cases(corpus_root: Path) -> list[_Case]:
    """Red-team cases plus A5 scenarios, in a stable order."""
    cases = [
        _Case(id=c.id, user=c.user, query=c.query, chunks=list(c.chunks))
        for c in load_red_team_corpus(corpus_root)
    ]
    cases += [_Case(id=s.id, user=s.user, query=s.title, chunks=list(s.chunks)) for s in SCENARIOS]
    return cases


def _replay_case(case: _Case, *, guard_factory: Callable[[], ContextGuard]) -> DeterminismResult:
    """Guard the same input twice with fresh guards and compare decision views."""
    first = guard_factory()
    first.guard(case.user, case.query, list(case.chunks))
    stored = first.last_evidence()

    second = guard_factory()
    second.guard(case.user, case.query, list(case.chunks))
    recomputed = second.last_evidence()

    matched = stored is not None and recomputed is not None and replay_matches(stored, recomputed)
    _record_replay_mismatch(mismatch=not matched)
    return DeterminismResult(case_id=case.id, matched=matched)


def run_determinism(
    corpus_root: Path | None = None,
    *,
    policy_path: str | Path = DEFAULT_POLICY,
    guard_factory: Callable[[], ContextGuard] | None = None,
) -> DeterminismReport:
    """Sweep replay determinism over the red-team plus A5 corpus.

    ``guard_factory`` is injectable so a test can swap in a non-deterministic stub
    and prove the harness can fail.
    """
    from contextguard_eval_harness.red_team import RED_TEAM_DIR

    root = corpus_root if corpus_root is not None else RED_TEAM_DIR
    factory = guard_factory or (lambda: ContextGuard.from_policy(policy_path))
    results = [_replay_case(c, guard_factory=factory) for c in _collect_cases(root)]
    return DeterminismReport(results=results)


__all__ = [
    "DeterminismReport",
    "DeterminismResult",
    "run_determinism",
]
