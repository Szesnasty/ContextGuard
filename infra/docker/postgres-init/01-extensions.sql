-- ContextGuard Postgres init (runs once on first volume creation).
-- Ensures pgvector is available so phase 2 (embeddings) can rely on it.
CREATE EXTENSION IF NOT EXISTS vector;
