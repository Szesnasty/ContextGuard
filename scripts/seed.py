"""`make seed` - enqueue ingestion of the seed corpus, then drain it (B2.2).

The end-to-end Tier-A path: load the planted-leak tenant corpus, chunk it, push
one ``ingest_chunks`` job onto the RQ ``ingest`` queue, then run a burst worker
that processes the job in-process and prints what landed. This is the demo that
proves ingestion runs **off the request path**: by the time ``/v1/query`` is
called, enrichment + embeddings are already in pgvector.

    make up && make seed

Needs the compose stack (Postgres + Redis + Ollama) and the ``[ingest]`` /
``[pgvector]`` / ``[embeddings]`` extras (dev group installs them).
"""

from __future__ import annotations

from contextguard.db.evidence import create_evidence_schema
from contextguard.jobs.ingest import IngestReport, enqueue_ingest
from contextguard.jobs.worker import run_worker
from contextguard.retrieval.chunking import FixedSizeChunker, chunk_corpus
from contextguard.retrieval.store import create_schema, get_engine
from contextguard_eval_harness.corpus import load_corpus


def main() -> None:
    engine = get_engine()
    create_schema(engine)
    create_evidence_schema(engine)

    documents = list(load_corpus())
    chunks = chunk_corpus(documents, FixedSizeChunker())
    job = enqueue_ingest(chunks)
    print(f"seed: enqueued {len(chunks)} chunks from {len(documents)} documents (job {job.id})")

    # Drain the queue in-process so `make seed` is a single, synchronous demo.
    run_worker(burst=True)

    report = job.latest_result()
    result: IngestReport | None = getattr(report, "return_value", None)
    if result is None:
        print("seed: worker finished but no result was recorded")
        return
    print(f"seed: wrote {result.chunks_written} chunks")
    for classification, count in sorted(result.by_classification.items()):
        print(f"  {classification:<13} {count}")


if __name__ == "__main__":
    main()
