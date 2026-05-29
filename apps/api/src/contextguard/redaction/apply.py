"""Redaction application — mask detected spans before assembly (Milestone A4).

This is the library slice of phase-5 step 1 (ADR-005 line 3): given a chunk that
policy decided to ``redact``, replace the PII/secret span ranges in its text with
a stable placeholder *before* the chunk reaches the model context. The original
text is never logged or emitted — the evidence record carries only the masked
form and span counts.

Masking is offset-based and deterministic: spans are applied right-to-left so
earlier offsets stay valid. Placeholders preserve the span *type* (and PII
subtype) so an auditor can see *what kind* of data was removed without seeing it.
"""

from __future__ import annotations

from contextguard.core.types import Chunk, Span, SpanType


def _placeholder(span: Span) -> str:
    if span.type is SpanType.SECRET:
        return "[REDACTED:SECRET]"
    return f"[REDACTED:{span.subtype.upper()}]"


def redact_text(text: str, spans: list[Span]) -> str:
    """Return ``text`` with every span range replaced by a typed placeholder.

    Overlapping spans (e.g. a digit run inside a secret that also looks like a
    PII id) are coalesced: the earliest-starting span wins, with secrets winning
    ties, so the masked output never interleaves two placeholders.
    """
    if not spans:
        return text
    # Coalesce overlaps: sort by start (secrets before PII on a tie), then drop
    # any span that begins inside a span already kept.
    ordered = sorted(spans, key=lambda s: (s.start, 0 if s.type is SpanType.SECRET else 1, -s.end))
    disjoint: list[Span] = []
    for span in ordered:
        if disjoint and span.start < disjoint[-1].end:
            continue
        disjoint.append(span)
    # Apply from the end so each replacement does not shift earlier offsets.
    result = text
    for span in sorted(disjoint, key=lambda s: s.start, reverse=True):
        result = result[: span.start] + _placeholder(span) + result[span.end :]
    return result


def redact_chunk(chunk: Chunk) -> Chunk:
    """Return a copy of ``chunk`` with PII + secret spans masked in its text.

    The returned chunk keeps its span metadata (counts feed the evidence record)
    but its ``text`` no longer contains the sensitive substrings.
    """
    spans = [*chunk.pii_spans, *chunk.secret_spans]
    return chunk.model_copy(update={"text": redact_text(chunk.text, spans)})


__all__ = ["redact_chunk", "redact_text"]
