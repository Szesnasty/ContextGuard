"""SQLAlchemy models for the pgvector-backed chunk store (Milestone B1.3, ADR-008).

This module is part of the optional ``[pgvector]`` tier (ADR-010): importing it
pulls SQLAlchemy + pgvector, so it lives off the zero-infra core path. The
``chunks`` table holds one embedded chunk per row, carrying the tenant and
classification the policy layer enforces later, plus enrichment columns that stay
nullable until phase 3 fills them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Matches the default local embedder (nomic-embed-text via Ollama). Switching to
# the cloud backend (1536-d) requires a migration that widens this column.
EMBEDDING_DIM = 768


class Base(DeclarativeBase):
    """Declarative base for ContextGuard persistence models."""


class ChunkRow(Base):
    """One embedded chunk. ``id`` is the chunker's stable hash (ADR-007)."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, index=True)
    tenant: Mapped[str] = mapped_column(String, index=True)
    classification: Mapped[str] = mapped_column(String, index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    # Named ``metadata`` in the database; ``metadata`` is reserved on the
    # declarative class, so the attribute is ``chunk_metadata``.
    chunk_metadata: Mapped[dict[str, str]] = mapped_column("metadata", JSONB, default=dict)
    # Enrichment columns (nullable now; populated by the phase-3 pipeline).
    pii_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secret_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvidenceRow(Base):
    """One persisted ``EvidenceRecord`` (Milestone B4.2, ADR-006).

    The full record lives in the ``record`` JSONB column (the frozen v1.0
    contract); ``tenant``, ``user_sub``, ``created_at``, and ``policies_triggered``
    are denormalized into indexed columns so audit queries (per tenant, per user,
    per fired policy) do not scan the JSON. By construction the record carries no
    original sensitive text (ADR-006 redaction-in-evidence invariant).
    """

    __tablename__ = "evidence"

    query_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant: Mapped[str] = mapped_column(String, index=True)
    user_sub: Mapped[str] = mapped_column(String, index=True)
    schema_version: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # JSONB array of fired rule ids; GIN-indexed for containment (`@>`) queries.
    policies_triggered: Mapped[list[str]] = mapped_column(JSONB, default=list)
    record: Mapped[dict[str, Any]] = mapped_column(JSONB)


__all__ = ["EMBEDDING_DIM", "Base", "ChunkRow", "EvidenceRow"]
