"""Background jobs (Redis + RQ) for ingestion. Optional ``[ingest]`` extra. Phase 3.

The job *body* (:func:`~contextguard.jobs.ingest.ingest_chunks`,
:class:`~contextguard.jobs.ingest.IngestReport`) is re-exported here because it
depends only on ``contextguard`` + ``contextguard_contracts``. The queue client
(``enqueue_ingest`` / the worker) pulls RQ + Redis lazily, so importing this
package stays light (ADR-010).
"""

from __future__ import annotations

from contextguard.jobs.ingest import DEFAULT_QUEUE, IngestReport, ingest_chunks

__all__ = ["DEFAULT_QUEUE", "IngestReport", "ingest_chunks"]
