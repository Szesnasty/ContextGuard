"""Background ingestion job: enrich + embed + persist chunks (Milestone B2.2).

Moves the heavy half of ingestion - enrichment, embedding, and the pgvector
upsert - **off the request path** into an RQ worker. ``/v1/query`` never embeds
or classifies; it only reads what this job has already landed.

The job function :func:`ingest_chunks` takes plain :class:`Chunk` objects
(``contextguard_contracts``) and nothing heavier, so it is picklable by RQ and
runs in a worker that needs only ``contextguard`` installed - it never imports
the eval-harness corpus loader (which depends on *this* package). The seed CLI
does the cheap load+chunk and enqueues the result.

RQ + Redis are the optional ``[ingest]`` extra (Tier A, ADR-010); both are
imported lazily inside :func:`enqueue_ingest` so importing this module - or the
zero-infra core - never pulls a queue client.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from contextguard_contracts.models import Chunk

if TYPE_CHECKING:
    from redis import Redis
    from rq.job import Job
    from sqlalchemy import Engine

    from contextguard.retrieval.embeddings import Embedder

DEFAULT_QUEUE = "ingest"


@dataclass(frozen=True)
class IngestReport:
    """Outcome of one ingestion run. Picklable so it survives as the job result."""

    chunks_written: int
    by_classification: dict[str, int]


def ingest_chunks(
    chunks: Sequence[Chunk],
    *,
    engine: Engine | None = None,
    embedder: Embedder | None = None,
) -> IngestReport:
    """Enrich, embed, and upsert ``chunks``; return what landed (the RQ job body).

    Runs in the worker process. ``engine`` and ``embedder`` default to the
    environment-configured live components, so the picklable call sent over the
    queue is just ``ingest_chunks(chunks)`` - heavy handles are built worker-side.
    """
    from contextguard.retrieval.embeddings import get_embedder
    from contextguard.retrieval.store import (
        classification_distribution,
        get_engine,
        upsert_chunks,
    )
    from contextguard.risk import enrich

    resolved_engine = engine or get_engine()
    resolved_embedder = embedder or get_embedder()

    enriched = [enrich(chunk) for chunk in chunks]
    written = upsert_chunks(resolved_engine, enriched, resolved_embedder)
    return IngestReport(
        chunks_written=written,
        by_classification=classification_distribution(resolved_engine),
    )


def enqueue_ingest(
    chunks: Sequence[Chunk],
    *,
    connection: Redis | None = None,
    queue_name: str = DEFAULT_QUEUE,
) -> Job:
    """Enqueue :func:`ingest_chunks` onto the RQ ``ingest`` queue (Tier A).

    Lazily imports RQ + Redis so the queue client is only required when ingestion
    is actually dispatched. ``connection`` defaults to ``REDIS_URL``.
    """
    from rq import Queue

    from contextguard.jobs.worker import get_connection

    queue = Queue(queue_name, connection=connection or get_connection())
    return queue.enqueue(ingest_chunks, list(chunks))


__all__ = ["DEFAULT_QUEUE", "IngestReport", "enqueue_ingest", "ingest_chunks"]
