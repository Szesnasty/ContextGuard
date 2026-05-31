"""create evidence table (JSONB persistence, Milestone B4.2, ADR-006).

Revision ID: 0002_create_evidence
Revises: 0001_create_chunks
Create Date: 2026-05-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002_create_evidence"
down_revision: str | None = "0001_create_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("query_id", sa.String(), primary_key=True),
        sa.Column("tenant", sa.String(), nullable=False),
        sa.Column("user_sub", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policies_triggered", JSONB(), nullable=False),
        sa.Column("record", JSONB(), nullable=False),
    )
    op.create_index("ix_evidence_tenant", "evidence", ["tenant"])
    op.create_index("ix_evidence_user_sub", "evidence", ["user_sub"])
    op.create_index("ix_evidence_created_at", "evidence", ["created_at"])
    # GIN index for JSONB containment (`policies_triggered @> '["rule-id"]'`):
    # answers "which queries fired this policy?" without scanning the table.
    op.create_index(
        "ix_evidence_policies_triggered_gin",
        "evidence",
        ["policies_triggered"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_policies_triggered_gin", table_name="evidence")
    op.drop_index("ix_evidence_created_at", table_name="evidence")
    op.drop_index("ix_evidence_user_sub", table_name="evidence")
    op.drop_index("ix_evidence_tenant", table_name="evidence")
    op.drop_table("evidence")
