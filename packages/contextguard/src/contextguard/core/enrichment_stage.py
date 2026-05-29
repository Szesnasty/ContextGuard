"""Pre-retrieval enrichment stage (Milestone A4, ADR-005 line 1 support).

Runs the zero-infra detectors over each candidate chunk *before* policy
evaluation, so the policy engine and redaction can act on PII/secret spans and
risk signals. Chunks that already carry spans/signals are left untouched
(enrichment happened at ingestion in the Tier A path).
"""

from __future__ import annotations

from contextguard.core.pipeline import PipelineContext
from contextguard.risk import enrich


class EnrichmentStage:
    """Annotate candidate chunks with PII/secret spans and risk signals."""

    name = "pre_retrieval"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.candidate_chunks = [
            chunk
            if (chunk.pii_spans or chunk.secret_spans or chunk.risk_signals)
            else enrich(chunk)
            for chunk in ctx.candidate_chunks
        ]
        return ctx


__all__ = ["EnrichmentStage"]
