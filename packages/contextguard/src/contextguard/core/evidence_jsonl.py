"""Default evidence sink for the zero-infra core (ADR-010).

The core's default evidence output is a plain ``dict`` returned by
``last_evidence()`` — no database in the core path. If an ``evidence_path`` is
configured, each record is also appended as one JSON line (JSONL) to disk. That
is the entire default story: no Postgres, no network. The ``[postgres]`` extra
wires a durable sink later (phase 5 / Milestone B).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from contextguard.core.types import EvidenceRecord


@runtime_checkable
class EvidenceSink(Protocol):
    """Where ``guard()`` writes one evidence record per query.

    The structural contract both the zero-infra :class:`JsonlEvidenceSink` and
    the Tier-A ``PostgresEvidenceSink`` satisfy, so the sink is injectable into
    :class:`~contextguard.core.guard.ContextGuard` without the core importing any
    database (ADR-010).
    """

    def emit(self, record: EvidenceRecord) -> None:
        """Persist one evidence record."""
        ...

    def last_evidence(self) -> dict[str, object] | None:
        """Return the last emitted record as a plain dict (or ``None``)."""
        ...


class JsonlEvidenceSink:
    """Keep the last record in memory; optionally append JSONL to disk."""

    def __init__(self, evidence_path: str | Path | None = None) -> None:
        self._path = Path(evidence_path) if evidence_path is not None else None
        self._last: dict[str, object] | None = None

    def emit(self, record: EvidenceRecord) -> None:
        """Record one evidence entry (in memory, and on disk if configured)."""
        payload = record.model_dump(mode="json")
        self._last = payload
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def last_evidence(self) -> dict[str, object] | None:
        """Return the last emitted evidence as a plain dict (or ``None``)."""
        return self._last


__all__ = ["EvidenceSink", "JsonlEvidenceSink"]
