"""Risk scoring + classification of retrieved content (Milestone A4, phase-3 slice).

Independent, deterministic, zero-infra detectors plus an ``enrich`` helper that
combines them. Detect-only — no chunk is blocked or masked here; the policy
engine (mid-retrieval) and redaction (post-retrieval) act on what is found.
"""

from __future__ import annotations

from contextguard.risk.enrich import enrich
from contextguard.risk.injection import detect_injection, risk_score
from contextguard.risk.pii import detect_pii
from contextguard.risk.secrets import detect_secrets

__all__ = [
    "detect_injection",
    "detect_pii",
    "detect_secrets",
    "enrich",
    "risk_score",
]
