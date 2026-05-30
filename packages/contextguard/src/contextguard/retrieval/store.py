"""pgvector chunk store: embed, upsert, and k-NN search (Milestone B1.3, ADR-008).

Part of the optional ``[pgvector]`` tier (ADR-010). The store is deliberately
thin: it embeds chunks with an injected :class:`~contextguard.retrieval.embeddings.Embedder`,
upserts them idempotently (keyed on the chunk's stable id), and exposes an L2
k-NN search. The ``filters`` argument on :func:`knn` is wired now but unused in
phase 2 - it is the seam where the phase-4 policy layer pushes tenant and
classification predicates into the database.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from contextguard_contracts.models import Chunk
from sqlalchemy import Engine, Table, create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from contextguard.db.models import Base, ChunkRow
from contextguard.retrieval.embeddings import Embedder, Vector

_DEFAULT_DSN = "postgresql+psycopg://contextguard:contextguard@localhost:5432/contextguard"


@dataclass(frozen=True)
class Neighbour:
    """One k-NN hit: the stored chunk plus its distance to the query vector."""

    id: str
    doc_id: str
    tenant: str
    classification: str
    text: str
    distance: float
    metadata: dict[str, str]


def _normalise_dsn(dsn: str) -> str:
    """Force the psycopg3 driver so a bare ``postgresql://`` URL still works."""
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return dsn


def get_engine(dsn: str | None = None) -> Engine:
    """Create an engine from ``dsn`` or ``DATABASE_URL`` (psycopg3 driver)."""
    resolved = dsn or os.getenv("DATABASE_URL") or _DEFAULT_DSN
    return create_engine(_normalise_dsn(resolved))


def create_schema(engine: Engine) -> None:
    """Create the ``chunks`` table (test helper; production uses Alembic)."""
    Base.metadata.create_all(engine)


def upsert_chunks(engine: Engine, chunks: Sequence[Chunk], embedder: Embedder) -> int:
    """Embed and upsert chunks idempotently. Returns the number of rows written."""
    if not chunks:
        return 0
    vectors = embedder.embed([chunk.text for chunk in chunks])
    rows = [
        {
            "id": chunk.id,
            "doc_id": chunk.doc_id,
            "tenant": chunk.tenant,
            "classification": str(chunk.classification),
            "text": chunk.text,
            "embedding": vector,
            "metadata": dict(chunk.metadata),
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    # Insert against the Core table so dict keys are real DB column names
    # (``metadata``); the ORM maps that column to the ``chunk_metadata`` attribute
    # to avoid colliding with ``DeclarativeBase.metadata``.
    table = cast(Table, ChunkRow.__table__)
    stmt = insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.id],
        set_={
            "doc_id": stmt.excluded.doc_id,
            "tenant": stmt.excluded.tenant,
            "classification": stmt.excluded.classification,
            "text": stmt.excluded.text,
            "embedding": stmt.excluded.embedding,
            "metadata": stmt.excluded.metadata,
        },
    )
    with Session(engine) as session:
        session.execute(stmt)
        session.commit()
    return len(rows)


def knn(
    engine: Engine,
    query_vector: Vector,
    k: int = 5,
    filters: Mapping[str, str] | None = None,
) -> list[Neighbour]:
    """Return the ``k`` nearest chunks by L2 distance, closest first.

    ``filters`` maps column names to required values (applied as equality). It is
    unused in phase 2; the parameter exists for the phase-4 policy push-down.
    """
    distance = ChunkRow.embedding.l2_distance(query_vector)
    stmt = select(ChunkRow, distance.label("distance"))
    for column, value in (filters or {}).items():
        stmt = stmt.where(getattr(ChunkRow, column) == value)
    stmt = stmt.order_by(distance).limit(k)
    with Session(engine) as session:
        results = session.execute(stmt).all()
    return [
        Neighbour(
            id=row.id,
            doc_id=row.doc_id,
            tenant=row.tenant,
            classification=row.classification,
            text=row.text,
            distance=float(dist),
            metadata=dict(row.chunk_metadata),
        )
        for row, dist in results
    ]


def all_chunks(engine: Engine) -> list[Chunk]:
    """Return every stored chunk as a domain :class:`Chunk` (no embeddings).

    Used to bootstrap the in-memory BM25 index from whatever is seeded in
    pgvector, so the keyword and dense halves index the same chunk set without a
    separate corpus source.
    """
    from contextguard_contracts.enums import Classification

    with Session(engine) as session:
        rows = session.execute(select(ChunkRow).order_by(ChunkRow.id)).scalars().all()
    return [
        Chunk(
            id=row.id,
            doc_id=row.doc_id,
            tenant=row.tenant,
            text=row.text,
            classification=Classification(row.classification),
            metadata=dict(row.chunk_metadata),
        )
        for row in rows
    ]


__all__ = ["Neighbour", "all_chunks", "create_schema", "get_engine", "knn", "upsert_chunks"]
