"""create chunks table with pgvector embedding (ADR-008).

Revision ID: 0001_create_chunks
Revises:
Create Date: 2026-05-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from contextguard.db.models import EMBEDDING_DIM
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_create_chunks"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("doc_id", sa.String(), nullable=False),
        sa.Column("tenant", sa.String(), nullable=False),
        sa.Column("classification", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("metadata", JSONB(), nullable=False),
        sa.Column("pii_count", sa.Integer(), nullable=True),
        sa.Column("secret_count", sa.Integer(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"])
    op.create_index("ix_chunks_tenant", "chunks", ["tenant"])
    op.create_index("ix_chunks_classification", "chunks", ["classification"])
    # Approximate-NN index for cosine/L2 search. HNSW gives good recall without
    # the ivfflat "train after load" caveat.
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_l2_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_classification", table_name="chunks")
    op.drop_index("ix_chunks_tenant", table_name="chunks")
    op.drop_index("ix_chunks_doc_id", table_name="chunks")
    op.drop_table("chunks")
