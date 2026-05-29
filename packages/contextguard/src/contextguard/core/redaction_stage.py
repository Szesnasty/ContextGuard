"""Post-retrieval redaction stage (Milestone A4, ADR-005 line 3).

Applies the ``redact`` decisions made at mid-retrieval: for every chunk the
policy marked ``REDACTED``, the chunk's text is masked in place (PII + secret
spans replaced with typed placeholders) before it reaches the model context.
The original text is dropped here and never reaches the evidence record.
"""

from __future__ import annotations

from contextguard.core.pipeline import PipelineContext
from contextguard.core.types import Outcome
from contextguard.redaction import redact_chunk


class RedactionStage:
    """Mask the text of chunks decided ``REDACTED`` at mid-retrieval."""

    name = "post_retrieval"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        to_redact = {cid for cid, d in ctx.decisions.items() if d.outcome is Outcome.REDACTED}
        if not to_redact:
            return ctx
        ctx.candidate_chunks = [
            redact_chunk(chunk) if chunk.id in to_redact else chunk
            for chunk in ctx.candidate_chunks
        ]
        return ctx


__all__ = ["RedactionStage"]
