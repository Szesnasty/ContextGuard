"""Closed enumerations shared across the ContextGuard contract surface.

These are the vocabulary the whole system agrees on: classification levels,
per-chunk outcomes, risk categories, and span kinds. Keeping them in one place
(and exporting them to TypeScript later) means Python and the frontend cannot
drift apart on what, e.g., ``confidential`` means.
"""

from __future__ import annotations

from enum import StrEnum


class Classification(StrEnum):
    """Sensitivity label attached to a chunk/document, lowest to highest."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Outcome(StrEnum):
    """What the guard decided to do with a single chunk."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    REDACTED = "redacted"


class RiskType(StrEnum):
    """Adversarial signal categories a chunk may carry (filled from phase 3)."""

    INJECTION = "injection"
    ROLE_OVERRIDE = "role_override"
    EXFILTRATION = "exfiltration"
    HIDDEN_TEXT = "hidden_text"
    TOOL_INSTRUCTION = "tool_instruction"


class SpanType(StrEnum):
    """Kind of sensitive span detected within a chunk's text."""

    PII = "pii"
    SECRET = "secret"  # noqa: S105 - enum label, not a credential


__all__ = ["Classification", "Outcome", "RiskType", "SpanType"]
