"""Red-team corpus loader — declarative attack cases + golden decisions (B5.1).

The corpus lives under ``data/red-team-corpora/*.yaml``; each file holds one or
more *cases*, and each case is one attack against the firewall that ships with
its **expected decision** (the golden label) per chunk. A security reviewer reads
these as data (YAML), not Python, and the golden label is what turns the harness
into a regression gate rather than a smoke test.

This module is **zero-infra** — it reads files and parses ``pyyaml``, nothing
heavier — mirroring :mod:`contextguard_eval_harness.corpus`. It builds plain
contract objects (:class:`~contextguard_contracts.UserContext`,
:class:`~contextguard_contracts.Chunk`) so the runner can call ``guard.guard()``
directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from contextguard_contracts import Chunk, Outcome, UserContext

# Repo root = four parents up (…/packages/eval-harness/src/contextguard_eval_harness/
# red_team.py → repo root).
_REPO_ROOT = Path(__file__).resolve().parents[4]
RED_TEAM_DIR = _REPO_ROOT / "data" / "red-team-corpora"


@dataclass(frozen=True)
class ChunkExpectation:
    """The golden decision the firewall must reach for one chunk."""

    outcome: Outcome
    rule: str | None = None
    redacted_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class RedTeamCase:
    """One adversarial case: who asks, what chunks, and the expected verdict."""

    id: str
    attack_class: str
    title: str
    user: UserContext
    query: str
    chunks: list[Chunk]
    expectations: dict[str, ChunkExpectation]
    sensitive_marker: str
    benign_marker: str
    source: Path = field(default=RED_TEAM_DIR, compare=False)

    @property
    def attack_chunk_ids(self) -> tuple[str, ...]:
        """Chunk ids whose golden decision is *not* ``allowed`` (the attacks)."""
        return tuple(
            cid for cid, exp in self.expectations.items() if exp.outcome is not Outcome.ALLOWED
        )


def _parse_expectation(raw: dict[str, object]) -> ChunkExpectation:
    outcome = Outcome(str(raw["outcome"]))
    rule = raw.get("rule")
    types = raw.get("redacted_types") or []
    if not isinstance(types, list):
        raise ValueError(f"redacted_types must be a list, got {types!r}")
    return ChunkExpectation(
        outcome=outcome,
        rule=str(rule) if rule is not None else None,
        redacted_types=tuple(str(t) for t in types),
    )


def _parse_case(raw: dict[str, object], source: Path) -> RedTeamCase:
    required = ("id", "attack_class", "title", "user", "query", "chunks")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"{source} case missing keys: {', '.join(missing)}")

    user = UserContext.model_validate(raw["user"])
    chunks: list[Chunk] = []
    expectations: dict[str, ChunkExpectation] = {}
    raw_chunks = raw["chunks"]
    if not isinstance(raw_chunks, list) or not raw_chunks:
        raise ValueError(f"{source} case {raw['id']!r} must list at least one chunk")
    for raw_chunk in raw_chunks:
        if not isinstance(raw_chunk, dict):
            raise ValueError(f"{source} case {raw['id']!r} has a non-mapping chunk")
        expect_raw = raw_chunk.get("expect")
        if not isinstance(expect_raw, dict):
            raise ValueError(f"{source} chunk {raw_chunk.get('id')!r} is missing `expect`")
        fields = {k: v for k, v in raw_chunk.items() if k != "expect"}
        chunk = Chunk.model_validate(fields)
        chunks.append(chunk)
        expectations[chunk.id] = _parse_expectation(expect_raw)

    if not any(exp.outcome is not Outcome.ALLOWED for exp in expectations.values()):
        raise ValueError(f"{source} case {raw['id']!r} is not an attack (nothing is stopped)")

    return RedTeamCase(
        id=str(raw["id"]),
        attack_class=str(raw["attack_class"]),
        title=str(raw["title"]),
        user=user,
        query=str(raw["query"]),
        chunks=chunks,
        expectations=expectations,
        sensitive_marker=str(raw["sensitive_marker"]),
        benign_marker=str(raw["benign_marker"]),
        source=source,
    )


def load_red_team_corpus(root: Path = RED_TEAM_DIR) -> list[RedTeamCase]:
    """Load every red-team case under ``root``, ordered by (file path, file order).

    Sorting by path makes the load order deterministic so the harness and report
    are byte-stable across runs.
    """
    cases: list[RedTeamCase] = []
    for path in sorted(root.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw is None:
            continue
        if not isinstance(raw, list):
            raise ValueError(f"{path} must be a YAML list of cases")
        for raw_case in raw:
            if not isinstance(raw_case, dict):
                raise ValueError(f"{path} contains a non-mapping case")
            cases.append(_parse_case(raw_case, path))
    return cases


__all__ = [
    "RED_TEAM_DIR",
    "ChunkExpectation",
    "RedTeamCase",
    "load_red_team_corpus",
]
