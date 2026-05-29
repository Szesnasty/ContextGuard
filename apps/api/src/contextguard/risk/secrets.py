"""Regex secret detector — zero-infra default (Milestone A4, phase-3 slice).

Independent detector (defense in depth): secrets are found by their own pattern
pack, separate from PII and injection heuristics, so one detector's blind spot
does not blind the others. Detect-only — masking happens in
:mod:`contextguard.redaction`.

The pure-regex pack is the zero-infra default; the entropy-based
``detect-secrets`` engine is an opt-in ``[secrets]`` extra wired in Milestone B.
"""

from __future__ import annotations

import re
from re import Pattern

from contextguard.core.types import Span, SpanType

# subtype -> compiled pattern, most specific first for deterministic precedence.
_SECRET_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    # Generic "key/secret/token/password = <value>" assignments.
    (
        "generic_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*"
            r"['\"]?([A-Za-z0-9_\-]{8,})['\"]?"
        ),
    ),
)


def detect_secrets(text: str) -> list[Span]:
    """Return non-overlapping secret spans found in ``text`` (deterministic order)."""
    spans: list[Span] = []
    taken: list[tuple[int, int]] = []
    for subtype, pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            # For assignments, mask only the secret value (group 1) when present.
            start = match.start(1) if match.groups() else match.start()
            end = match.end(1) if match.groups() else match.end()
            if any(start < t_end and t_start < end for t_start, t_end in taken):
                continue
            taken.append((start, end))
            spans.append(Span(type=SpanType.SECRET, subtype=subtype, start=start, end=end))
    spans.sort(key=lambda s: (s.start, s.end))
    return spans


__all__ = ["detect_secrets"]
