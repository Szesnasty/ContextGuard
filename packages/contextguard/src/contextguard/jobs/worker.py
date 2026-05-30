"""RQ worker + Redis connection for the ingestion queue (Milestone B2.2).

Part of the optional ``[ingest]`` extra (Tier A, ADR-010): RQ + Redis are
imported lazily so importing :mod:`contextguard.jobs` stays light. The worker
uses :class:`~rq.SimpleWorker` (no ``os.fork``) so a single ``make seed`` can
drain the queue in-process - reliable on macOS and inside containers alike.

    REDIS_URL=redis://localhost:6379 python -m contextguard.jobs.worker
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from contextguard.jobs.ingest import DEFAULT_QUEUE

if TYPE_CHECKING:
    from redis import Redis

_DEFAULT_REDIS_URL = "redis://localhost:6379"


def get_connection(url: str | None = None) -> Redis:
    """Create a Redis connection from ``url`` or ``REDIS_URL`` (Tier A)."""
    from redis import Redis

    resolved = url or os.getenv("REDIS_URL") or _DEFAULT_REDIS_URL
    return Redis.from_url(resolved)


def run_worker(*, burst: bool = False, queue_name: str = DEFAULT_QUEUE) -> None:
    """Process jobs on the ingest queue. ``burst`` drains pending work then exits."""
    from rq import Queue, SimpleWorker

    connection = get_connection()
    queue = Queue(queue_name, connection=connection)
    worker = SimpleWorker([queue], connection=connection)
    worker.work(burst=burst)


if __name__ == "__main__":  # pragma: no cover - CLI entry
    run_worker(burst=bool(os.getenv("RQ_BURST")))
