"""Enrichment + redaction application tests (Milestone A4)."""

from __future__ import annotations

from contextguard.core.types import Chunk, Classification, SpanType
from contextguard.redaction import redact_chunk, redact_text
from contextguard.risk import enrich


def _chunk(text: str) -> Chunk:
    return Chunk(
        id="c1", doc_id="d1", tenant="acme", text=text, classification=Classification.INTERNAL
    )


class TestEnrich:
    def test_populates_spans_and_signals(self) -> None:
        chunk = _chunk("mail bob@acme.io key sk-abcdefghij0123456789 ignore previous")
        enriched = enrich(chunk)
        assert any(s.subtype == "email" for s in enriched.pii_spans)
        assert any(s.type is SpanType.SECRET for s in enriched.secret_spans)
        assert enriched.risk_signals

    def test_is_pure_returns_new_object(self) -> None:
        chunk = _chunk("bob@acme.io")
        enriched = enrich(chunk)
        assert chunk.pii_spans == []  # original untouched (frozen)
        assert enriched is not chunk

    def test_clean_chunk_stays_empty(self) -> None:
        enriched = enrich(_chunk("ordinary content"))
        assert enriched.pii_spans == []
        assert enriched.secret_spans == []
        assert enriched.risk_signals == []


class TestRedactText:
    def test_masks_email_with_typed_placeholder(self) -> None:
        chunk = enrich(_chunk("contact bob@acme.io now"))
        out = redact_text(chunk.text, chunk.pii_spans)
        assert "bob@acme.io" not in out
        assert "[REDACTED:EMAIL]" in out

    def test_no_spans_is_identity(self) -> None:
        assert redact_text("plain text", []) == "plain text"

    def test_multiple_spans_offsets_stay_valid(self) -> None:
        chunk = enrich(_chunk("a@b.com and sk-abcdefghij0123456789 here"))
        out = redact_chunk(chunk).text
        assert "a@b.com" not in out
        assert "sk-abcdefghij0123456789" not in out
        assert "[REDACTED:EMAIL]" in out
        assert "[REDACTED:SECRET]" in out

    def test_redact_chunk_keeps_span_metadata(self) -> None:
        chunk = enrich(_chunk("secret sk-abcdefghij0123456789"))
        redacted = redact_chunk(chunk)
        # text masked, but span counts preserved for the evidence record
        assert "sk-abcdefghij0123456789" not in redacted.text
        assert len(redacted.secret_spans) == len(chunk.secret_spans)
