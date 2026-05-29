"""Alembic environment for the ContextGuard pgvector store (ADR-008).

The database URL comes from ``DATABASE_URL`` (psycopg3 driver enforced), so the
same migrations run against the compose Postgres locally and in CI.
"""

from __future__ import annotations

import os

from alembic import context
from contextguard.db.models import Base
from sqlalchemy import engine_from_config, pool

config = context.config


def _database_url() -> str:
    dsn = os.getenv(
        "DATABASE_URL",
        "postgresql://contextguard:contextguard@localhost:5432/contextguard",
    )
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return dsn


config.set_main_option("sqlalchemy.url", _database_url())
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
