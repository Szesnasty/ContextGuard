"""Regex PII detector — zero-infra default (Milestone A4, phase-3 slice).

Detect-only (ADR-005 line 3 *decides* later): this module finds personally
identifiable information in chunk text and returns :class:`Span` offsets. It
masks nothing — redaction is applied in :mod:`contextguard.redaction`.

These are deterministic regex packs (EN + PL), the zero-infra default. The
heavier, higher-recall Presidio recognizers are an opt-in ``[pii]`` extra wired
in Milestone B (phase 3). Patterns favour precision: a missed match degrades
gracefully (chunk still policy-checked), a false mask would corrupt context.
"""

from __future__ import annotations

import re
from re import Pattern

from contextguard.core.types import Span, SpanType

# subtype -> compiled pattern. Order is stable for deterministic span output.
_PII_PATTERNS: dict[str, Pattern[str]] = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    # PL PESEL: exactly 11 digits, not part of a longer number.
    "pesel": re.compile(r"(?<!\d)\d{11}(?!\d)"),
    # PL NIP: 10 digits, optionally dashed (123-456-32-18 / 1234563218).
    "nip": re.compile(r"(?<!\d)\d{3}-?\d{3}-?\d{2}-?\d{2}(?!\d)"),
    # Credit-card-like: 13-16 digits in groups of four (spaces/dashes optional).
    "credit_card": re.compile(r"(?<!\d)(?:\d[ -]?){12,15}\d(?!\d)"),
    "phone": re.compile(r"(?<![\w])(?:\+?\d{1,3}[ -]?)?(?:\d[ -]?){8,11}\d(?![\w])"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

# Detect more specific kinds first so a PESEL is not also reported as a phone.
_PRIORITY = ("email", "ipv4", "credit_card", "pesel", "nip", "phone")


def detect_pii(text: str) -> list[Span]:
    """Return non-overlapping PII spans found in ``text`` (deterministic order)."""
    spans: list[Span] = []
    taken: list[tuple[int, int]] = []
    for subtype in _PRIORITY:
        for match in _PII_PATTERNS[subtype].finditer(text):
            start, end = match.start(), match.end()
            if any(start < t_end and t_start < end for t_start, t_end in taken):
                continue
            taken.append((start, end))
            spans.append(Span(type=SpanType.PII, subtype=subtype, start=start, end=end))
    spans.sort(key=lambda s: (s.start, s.end))
    return spans


__all__ = ["detect_pii"]
