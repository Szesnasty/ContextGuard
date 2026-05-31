"""The ContextGuard domain models — the single source of truth (ADR-004).

Every consumer (core ``guard()``, the API layer, the eval-harness, and the
generated TypeScript types) imports these models from here. They are Pydantic v2
models with a strict config: unknown fields are rejected and instances are
frozen, so a contract violation surfaces as a ``ValidationError`` at the
boundary instead of a silent bug deep in the pipeline.

``EvidenceRecord`` is the public, versioned contract. Its ``schema_version`` is
a ``Literal`` and a committed JSON Schema snapshot guards it against silent
drift (see ``scripts/gen_schemas.py`` and the snapshot test). Bumping the
version is a deliberate, reviewed act — frozen as **v1.0** and governed by
ADR-006 (semver policy: additive fields bump MINOR, removals/retypes bump
MAJOR).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import Classification, Outcome, RiskType, SpanType

EVIDENCE_SCHEMA_VERSION: Literal["1.0"] = "1.0"
"""Frozen evidence-record schema version (v1.0, ADR-006). Bumping requires an ADR."""

_STRICT = ConfigDict(extra="forbid", frozen=True)


class Span(BaseModel):
    """A half-open ``[start, end)`` character range of sensitive text."""

    model_config = _STRICT

    type: SpanType
    subtype: str
    start: int
    end: int

    @model_validator(mode="after")
    def _check_bounds(self) -> Span:
        if self.start < 0:
            raise ValueError("span start must be non-negative")
        if self.end < self.start:
            raise ValueError("span end must be >= start")
        return self


class RiskSignal(BaseModel):
    """An adversarial signal detected in a chunk, with a confidence weight."""

    model_config = _STRICT

    type: RiskType
    weight: float
    evidence: str


class UserContext(BaseModel):
    """Who is asking, and under what authority — the input to policy."""

    model_config = _STRICT

    sub: str
    tenant: str
    role: str
    purpose: str
    labels: list[str] = []


class Chunk(BaseModel):
    """A retrieved unit of context. Enrichment fields stay empty until phase 3."""

    model_config = _STRICT

    id: str
    doc_id: str
    tenant: str
    text: str
    classification: Classification
    metadata: dict[str, str] = {}
    pii_spans: list[Span] = []
    secret_spans: list[Span] = []
    risk_signals: list[RiskSignal] = []


class ChunkDecision(BaseModel):
    """The guard's verdict for one chunk, with auditable reasons."""

    model_config = _STRICT

    chunk_id: str
    outcome: Outcome
    reasons: list[str] = []
    policies_triggered: list[str] = []


class GuardedContext(BaseModel):
    """The result of ``guard()``: what survived, every decision, token deltas."""

    model_config = _STRICT

    allowed_chunks: list[Chunk] = []
    decisions: list[ChunkDecision] = []
    tokens_before: int = 0
    tokens_after: int = 0


class EvidenceMetrics(BaseModel):
    """Aggregate counters describing one guarded query."""

    model_config = _STRICT

    chunks_retrieved: int = 0
    chunks_allowed: int = 0
    chunks_blocked: int = 0
    chunks_redacted: int = 0
    tokens_before: int = 0
    tokens_after: int = 0


class EvidenceRecord(BaseModel):
    """The public, versioned audit record for one guarded query (v1, ADR-006).

    This is the contract ADR-004 promises stays semver-stable. The JSON Schema
    snapshot test makes any change to its shape a deliberate, reviewed act. By
    construction the record never carries original sensitive text: redaction
    runs before assembly, so only counts, decisions, and reasons are stored.
    """

    model_config = _STRICT

    schema_version: Literal["1.0"] = EVIDENCE_SCHEMA_VERSION
    query_id: str
    user: UserContext
    query: str
    decisions: list[ChunkDecision] = []
    metrics: EvidenceMetrics
    policies_triggered: list[str] = []
    created_at: datetime


class RetrievedChunk(BaseModel):
    """One retrieval hit returned to the caller: identity, text, fused score."""

    model_config = _STRICT

    id: str
    doc_id: str
    tenant: str
    classification: Classification
    text: str
    score: float
    metadata: dict[str, str] = {}


class QueryRequest(BaseModel):
    """A RAG query: what is asked and how many chunks to retrieve.

    Identity is NOT carried here - it is derived from the verified Bearer token
    at the HTTP boundary (ADR-015), never asserted by the client body.
    """

    model_config = _STRICT

    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=50)


class QueryResponse(BaseModel):
    """The grounded answer plus the retrieval hits and the guard's verdict."""

    model_config = _STRICT

    answer: str
    retrieved_chunks: list[RetrievedChunk] = []
    guarded_context: GuardedContext


class GuardRequest(BaseModel):
    """A scan-only request: the query plus the candidate chunks to adjudicate.

    Identity is NOT carried here - it is derived from the verified Bearer token
    at the HTTP boundary (ADR-015). The caller supplies the chunks to guard, so
    the scan runs without retrieval or a model call (Milestone B3.3).
    """

    model_config = _STRICT

    query: str = Field(min_length=1)
    candidate_chunks: list[Chunk] = []


__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "Chunk",
    "ChunkDecision",
    "Classification",
    "EvidenceMetrics",
    "EvidenceRecord",
    "GuardRequest",
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
]
