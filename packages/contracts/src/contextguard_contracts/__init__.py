"""ContextGuard shared contracts — the single source of truth (ADR-004).

Import the domain vocabulary from here:

    from contextguard_contracts import Chunk, GuardedContext, EvidenceRecord
"""

from __future__ import annotations

from .enums import Classification, Outcome, RiskType, SpanType
from .models import (
    EVIDENCE_SCHEMA_VERSION,
    Chunk,
    ChunkDecision,
    EvidenceMetrics,
    EvidenceRecord,
    GuardedContext,
    QueryRequest,
    QueryResponse,
    RetrievedChunk,
    RiskSignal,
    Span,
    UserContext,
)

__version__ = "0.0.0"

__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "Chunk",
    "ChunkDecision",
    "Classification",
    "EvidenceMetrics",
    "EvidenceRecord",
    "GuardedContext",
    "Outcome",
    "QueryRequest",
    "QueryResponse",
    "RetrievedChunk",
    "RiskSignal",
    "RiskType",
    "Span",
    "SpanType",
    "UserContext",
    "__version__",
]
