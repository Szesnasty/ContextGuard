"""Tests for the contracts domain models (step 1.1)."""

from __future__ import annotations

from datetime import UTC, datetime

import contextguard_contracts as cc
import pytest
from contextguard_contracts import (
    EVIDENCE_SCHEMA_VERSION,
    Chunk,
    ChunkDecision,
    Classification,
    EvidenceMetrics,
    EvidenceRecord,
    GuardedContext,
    Outcome,
    RiskSignal,
    RiskType,
    Span,
    SpanType,
    UserContext,
)
from pydantic import BaseModel, ValidationError

PUBLIC_TYPES: list[type[BaseModel]] = [
    Span,
    RiskSignal,
    UserContext,
    Chunk,
    ChunkDecision,
    GuardedContext,
    EvidenceMetrics,
    EvidenceRecord,
]


def _user() -> UserContext:
    return UserContext(sub="u1", tenant="acme", role="sales", purpose="support")


def _chunk(**kw: object) -> Chunk:
    base: dict[str, object] = {
        "id": "c1",
        "doc_id": "d1",
        "tenant": "acme",
        "text": "hello",
        "classification": Classification.PUBLIC,
    }
    base.update(kw)
    return Chunk(**base)  # type: ignore[arg-type]


def _evidence() -> EvidenceRecord:
    return EvidenceRecord(
        query_id="q1",
        user=_user(),
        query="hi",
        metrics=EvidenceMetrics(),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_public_surface_importable() -> None:
    for name in (
        "Span",
        "RiskSignal",
        "UserContext",
        "Chunk",
        "ChunkDecision",
        "GuardedContext",
        "EvidenceMetrics",
        "EvidenceRecord",
        "Classification",
        "Outcome",
        "RiskType",
        "SpanType",
        "EVIDENCE_SCHEMA_VERSION",
    ):
        assert hasattr(cc, name), name


def test_chunk_enrichment_defaults_empty() -> None:
    c = _chunk()
    assert c.pii_spans == []
    assert c.secret_spans == []
    assert c.risk_signals == []
    assert c.metadata == {}


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        _chunk(unknown_field="x")


def test_models_are_frozen() -> None:
    c = _chunk()
    with pytest.raises(ValidationError):
        c.text = "mutated"


def test_span_bounds_validation() -> None:
    Span(type=SpanType.PII, subtype="email", start=0, end=5)  # ok
    Span(type=SpanType.PII, subtype="email", start=3, end=3)  # empty span ok
    with pytest.raises(ValidationError):
        Span(type=SpanType.PII, subtype="email", start=-1, end=2)
    with pytest.raises(ValidationError):
        Span(type=SpanType.PII, subtype="email", start=5, end=2)


@pytest.mark.parametrize("model", [_user(), _chunk(), _evidence(), GuardedContext()])
def test_serialization_roundtrip(model: BaseModel) -> None:
    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored == model


def test_evidence_record_minimal_and_version() -> None:
    rec = _evidence()
    assert rec.schema_version == "0.1"
    assert EVIDENCE_SCHEMA_VERSION == "0.1"


def test_chunk_decision_defaults() -> None:
    d = ChunkDecision(chunk_id="c1", outcome=Outcome.ALLOWED)
    assert d.reasons == []
    assert d.policies_triggered == []


def test_risk_signal_constructs() -> None:
    sig = RiskSignal(type=RiskType.INJECTION, weight=0.9, evidence="ignore previous")
    assert sig.weight == 0.9
