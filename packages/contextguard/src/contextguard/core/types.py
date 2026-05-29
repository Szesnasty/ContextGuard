"""Canonical domain vocabulary for the core (ADR-004).

Core modules import domain types *only* from here, never directly from
``contextguard_contracts``. This gives the adapter import-gate a single stable
surface to guard and decouples ``core`` from where the contracts physically
live. These are re-exports (identity-preserving), not redefinitions.
"""

from __future__ import annotations

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

__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "Chunk",
    "ChunkDecision",
    "Classification",
    "EvidenceMetrics",
    "EvidenceRecord",
    "GuardedContext",
    "Outcome",
    "RiskSignal",
    "RiskType",
    "Span",
    "SpanType",
    "UserContext",
]
