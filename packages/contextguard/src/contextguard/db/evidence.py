"""Durable evidence sink: persist ``EvidenceRecord`` to Postgres JSONB (B4.2).

Part of the optional ``[pgvector]`` tier (ADR-010): importing this module pulls
SQLAlchemy, so it lives off the zero-infra core path. It satisfies the core
:class:`~contextguard.core.evidence_jsonl.EvidenceSink` protocol structurally,
so ``ContextGuard(sink=PostgresEvidenceSink(engine))`` wires durable persistence
without the core ever importing a database.

The full record is stored as JSONB (the frozen v1.0 contract, ADR-006); audit
dimensions (tenant, user, fired policies, time) are denormalized into indexed
columns. ``replay(query_id)`` reads a record back byte-for-byte: the persisted
decision is the audit record of what happened, reproducible on demand.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Engine, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from contextguard.core.types import EvidenceRecord
from contextguard.db.models import Base, EvidenceRow


def create_evidence_schema(engine: Engine) -> None:
    """Create the ``evidence`` table (test helper; production uses Alembic)."""
    Base.metadata.create_all(engine, tables=[cast(Table, EvidenceRow.__table__)])


class PostgresEvidenceSink:
    """Persist evidence to Postgres JSONB; replay and query by audit dimension."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._last: dict[str, object] | None = None

    def emit(self, record: EvidenceRecord) -> None:
        """Upsert one evidence record (idempotent on ``query_id``)."""
        payload = record.model_dump(mode="json")
        self._last = payload
        row = {
            "query_id": record.query_id,
            "tenant": record.user.tenant,
            "user_sub": record.user.sub,
            "schema_version": record.schema_version,
            "created_at": record.created_at,
            "policies_triggered": list(record.policies_triggered),
            "record": payload,
        }
        table = cast(Table, EvidenceRow.__table__)
        stmt = insert(table).values([row])
        stmt = stmt.on_conflict_do_update(
            index_elements=[table.c.query_id],
            set_={
                "tenant": stmt.excluded.tenant,
                "user_sub": stmt.excluded.user_sub,
                "schema_version": stmt.excluded.schema_version,
                "created_at": stmt.excluded.created_at,
                "policies_triggered": stmt.excluded.policies_triggered,
                "record": stmt.excluded.record,
            },
        )
        with Session(self._engine) as session:
            session.execute(stmt)
            session.commit()

    def last_evidence(self) -> dict[str, object] | None:
        """Return the last emitted record as a plain dict (or ``None``)."""
        return self._last

    def replay(self, query_id: str) -> dict[str, object] | None:
        """Return the stored evidence record for ``query_id`` (or ``None``).

        Replay reproduces the immutable record of what the guard decided for that
        query: the persisted JSONB is returned exactly as it was emitted.
        """
        stmt = select(EvidenceRow.record).where(EvidenceRow.query_id == query_id)
        with Session(self._engine) as session:
            result = session.execute(stmt).scalar_one_or_none()
        return cast("dict[str, object] | None", result)

    def query_by_tenant(self, tenant: str) -> list[dict[str, object]]:
        """Return all stored records for ``tenant``, newest first."""
        stmt = (
            select(EvidenceRow.record)
            .where(EvidenceRow.tenant == tenant)
            .order_by(EvidenceRow.created_at.desc())
        )
        with Session(self._engine) as session:
            rows = session.execute(stmt).scalars().all()
        return [cast("dict[str, object]", r) for r in rows]

    def query_by_policy(self, rule_id: str) -> list[dict[str, object]]:
        """Return records whose ``policies_triggered`` contains ``rule_id``.

        Uses the JSONB containment operator (``@>``), served by the GIN index, so
        "which queries fired this policy?" stays a single indexed lookup.
        """
        stmt = (
            select(EvidenceRow.record)
            .where(EvidenceRow.policies_triggered.contains([rule_id]))
            .order_by(EvidenceRow.created_at.desc())
        )
        with Session(self._engine) as session:
            rows = session.execute(stmt).scalars().all()
        return [cast("dict[str, object]", r) for r in rows]


__all__ = ["PostgresEvidenceSink", "create_evidence_schema"]
