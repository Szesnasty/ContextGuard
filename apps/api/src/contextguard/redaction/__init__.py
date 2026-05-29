"""Redaction application — mask PII/secret spans before prompt assembly.

Zero-infra default uses offset-based masking over the spans produced by
:mod:`contextguard.risk`. The optional Presidio-backed masker is a Milestone B
extra; the public surface (``redact_text``/``redact_chunk``) stays the same.
"""

from __future__ import annotations

from contextguard.redaction.apply import redact_chunk, redact_text

__all__ = ["redact_chunk", "redact_text"]
