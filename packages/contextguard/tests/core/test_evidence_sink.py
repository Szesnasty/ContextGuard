"""Injectable evidence sink + replay-determinism tests (Milestone B4.2).

Pure and zero-infra: the ``EvidenceSink`` protocol and sink injection are exercised
with an in-memory fake — no database. The Postgres round-trip lives in
``tests/integration/test_evidence_store.py``.
"""

from __future__ import annotations

from contextguard.core import ContextGuard
from contextguard.core.evidence_jsonl import EvidenceSink, JsonlEvidenceSink
from contextguard.core.types import Chunk, Classification, EvidenceRecord, UserContext


def _user() -> UserContext:
    return UserContext(sub="u1", tenant="acme", role="sales", purpose="support")


def _chunks(n: int) -> list[Chunk]:
    return [
        Chunk(
            id=f"c{i}",
            doc_id="d1",
            tenant="acme",
            text=f"chunk number {i}",
            classification=Classification.PUBLIC,
        )
        for i in range(n)
    ]


class _RecordingSink:
    """An EvidenceSink that keeps every emitted record (structural fake)."""

    def __init__(self) -> None:
        self.records: list[EvidenceRecord] = []

    def emit(self, record: EvidenceRecord) -> None:
        self.records.append(record)

    def last_evidence(self) -> dict[str, object] | None:
        return self.records[-1].model_dump(mode="json") if self.records else None


def _decision_view(ev: dict[str, object]) -> dict[str, object]:
    """The deterministic part of a record (drops the per-run id + timestamp)."""
    return {
        "decisions": ev["decisions"],
        "metrics": ev["metrics"],
        "policies_triggered": ev["policies_triggered"],
        "user": ev["user"],
        "query": ev["query"],
        "schema_version": ev["schema_version"],
    }


def test_jsonl_sink_satisfies_protocol() -> None:
    assert isinstance(JsonlEvidenceSink(), EvidenceSink)


def test_recording_sink_satisfies_protocol() -> None:
    assert isinstance(_RecordingSink(), EvidenceSink)


def test_guard_emits_to_injected_sink() -> None:
    sink = _RecordingSink()
    guard = ContextGuard(sink=sink)
    guard.guard(_user(), "hi", _chunks(2))
    assert len(sink.records) == 1
    assert sink.records[0].metrics.chunks_allowed == 2


def test_guard_last_evidence_reads_injected_sink() -> None:
    sink = _RecordingSink()
    guard = ContextGuard(sink=sink)
    assert guard.last_evidence() is None
    guard.guard(_user(), "hi", _chunks(1))
    ev = guard.last_evidence()
    assert isinstance(ev, dict)
    assert ev["schema_version"] == "1.0"


def test_injected_sink_takes_precedence_over_evidence_path(tmp_path: object) -> None:
    sink = _RecordingSink()
    # evidence_path is ignored when an explicit sink is injected.
    guard = ContextGuard(sink=sink, evidence_path=tmp_path)  # type: ignore[arg-type]
    guard.guard(_user(), "hi", _chunks(1))
    assert len(sink.records) == 1


def test_replay_determinism_same_input_same_decision() -> None:
    """The deterministic core means a re-run reproduces the stored decision.

    Two guard runs over identical inputs differ only in the per-run ``query_id``
    and ``created_at``; every audited dimension (decisions, metrics, fired
    policies) is byte-identical. This is the invariant the replay harness checks:
    ``cg_replay_mismatch_total == 0``.
    """
    chunks = _chunks(3)
    first = _RecordingSink()
    second = _RecordingSink()
    ContextGuard(sink=first).guard(_user(), "hi", chunks)
    ContextGuard(sink=second).guard(_user(), "hi", chunks)

    a = first.records[0].model_dump(mode="json")
    b = second.records[0].model_dump(mode="json")
    assert a["query_id"] != b["query_id"]  # per-run identity differs
    assert _decision_view(a) == _decision_view(b)  # the decision is reproducible
