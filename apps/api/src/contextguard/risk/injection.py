"""Deterministic prompt-injection heuristics (Milestone A4, phase-3 slice).

Signals, not verdicts (phase-3 charter, ADR-005): this module surfaces
adversarial *signals* a chunk carries — it never decides to block. The policy
engine consumes the aggregate ``risk_score`` as an explicit input (ADR-005:
"risk score is an input to policy, never a hidden ``if``").

No ML, no LLM, no network: a closed set of regex patterns over chunk text, each
mapped to a :class:`RiskType` and a confidence ``weight``. A clean chunk yields
no signals.
"""

from __future__ import annotations

import re
from re import Pattern

from contextguard.core.types import RiskSignal, RiskType

# (RiskType, weight, pattern). Weights are deliberate, documented confidences.
_INJECTION_PATTERNS: tuple[tuple[RiskType, float, Pattern[str]], ...] = (
    (
        RiskType.INJECTION,
        0.9,
        re.compile(r"(?i)\bignore\s+(?:all\s+|the\s+)?(?:previous|prior|above)\b"),
    ),
    (
        RiskType.INJECTION,
        0.8,
        re.compile(r"(?i)\bdisregard\s+(?:all\s+)?(?:previous|prior|above|instructions)\b"),
    ),
    (
        RiskType.ROLE_OVERRIDE,
        0.85,
        re.compile(r"(?i)\byou\s+are\s+now\b|\bact\s+as\b|\bpretend\s+to\s+be\b"),
    ),
    (
        RiskType.ROLE_OVERRIDE,
        0.7,
        re.compile(r"(?i)\b(?:system\s+prompt|developer\s+message)\b"),
    ),
    (
        RiskType.EXFILTRATION,
        0.75,
        re.compile(
            r"(?i)\b(?:reveal|print|repeat|leak)\s+(?:your|the)\s+(?:prompt|instructions|system)\b"
        ),
    ),
    (
        RiskType.TOOL_INSTRUCTION,
        0.6,
        re.compile(r"(?i)\b(?:call|invoke|execute|run)\s+(?:the\s+)?(?:tool|function|command)\b"),
    ),
    # Hidden/zero-width characters used to smuggle instructions past humans.
    (RiskType.HIDDEN_TEXT, 0.95, re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")),
)


def detect_injection(text: str) -> list[RiskSignal]:
    """Return adversarial risk signals for ``text`` (deterministic order)."""
    signals: list[RiskSignal] = []
    for risk_type, weight, pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            evidence = match.group(0)
            if risk_type is RiskType.HIDDEN_TEXT:
                evidence = "zero-width or bidi control character"
            signals.append(RiskSignal(type=risk_type, weight=weight, evidence=evidence))
    return signals


def risk_score(signals: list[RiskSignal]) -> float:
    """Aggregate signal weights into a single 0..1 score (saturating max-combine)."""
    score = 0.0
    for signal in signals:
        score = score + signal.weight - score * signal.weight
    return round(score, 4)


__all__ = ["detect_injection", "risk_score"]
