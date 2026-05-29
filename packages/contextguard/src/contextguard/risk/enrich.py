"""Chunk enrichment — combine the independent detectors (Milestone A4).

``enrich`` runs the three detect-only packs (PII, secrets, injection) over a
chunk's text and returns a *new* chunk (models are frozen) with ``pii_spans``,
``secret_spans``, and ``risk_signals`` populated. It performs no I/O and is
deterministic, so it is safe to run inline in the zero-infra ``guard()`` path.

This is the library slice of phase 3: at Tier A the same enrichment runs in the
ingestion worker and is persisted; here it runs on the candidate chunks just
before policy evaluation so the policy can act on the signals.
"""

from __future__ import annotations

from contextguard.core.types import Chunk
from contextguard.risk.injection import detect_injection
from contextguard.risk.pii import detect_pii
from contextguard.risk.secrets import detect_secrets


def enrich(chunk: Chunk) -> Chunk:
    """Return a copy of ``chunk`` with PII/secret spans and risk signals filled."""
    return chunk.model_copy(
        update={
            "pii_spans": detect_pii(chunk.text),
            "secret_spans": detect_secrets(chunk.text),
            "risk_signals": detect_injection(chunk.text),
        }
    )


__all__ = ["enrich"]
