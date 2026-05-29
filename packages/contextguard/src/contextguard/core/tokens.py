"""Token counting for the zero-infra core (ADR-010).

Design constraint: the default token counter must work with **no network and no
heavy dependencies** — ``import contextguard.core`` may pull nothing heavier
than ``pydantic`` + ``pyyaml`` (ADR-010), and the core must run on a clean
machine with sockets blocked (the ``test_guard_no_network`` contract).

``tiktoken`` is therefore **not** the default: its first use downloads a BPE
vocabulary over the network, which would break offline/zero-infra guarantees.
Instead the default is a deterministic, pure-Python regex tokenizer that gives
stable counts everywhere. ``tiktoken`` remains available as an *optional*
encoder (``[tiktoken]`` extra) for callers who want exact model-specific counts
and accept the download; it is imported lazily, never at module top level.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

# Words, standalone punctuation, and whitespace runs each count as one token.
# Deterministic, dependency-free, and a reasonable proxy for BPE token counts.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def token_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` character offsets of each token in ``text``.

    Uses the same regex as :class:`RegexTokenCounter`, so a window of N spans
    contains exactly N tokens by :func:`count_tokens`. Offsets index the original
    string, which lets a token-windowed chunker slice text without losing the
    original whitespace between tokens.
    """
    return [(m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]


@runtime_checkable
class TokenCounter(Protocol):
    """Anything that can count tokens in a string."""

    def count(self, text: str) -> int: ...


class RegexTokenCounter:
    """Default zero-infra counter: pure-Python, deterministic, offline."""

    def count(self, text: str) -> int:
        return len(_TOKEN_RE.findall(text))


_DEFAULT = RegexTokenCounter()


def default_counter() -> TokenCounter:
    """Return the process-wide default (zero-infra) token counter."""
    return _DEFAULT


def count_tokens(text: str, *, counter: TokenCounter | None = None) -> int:
    """Count tokens in ``text`` using the default (or a supplied) counter."""
    return (counter or _DEFAULT).count(text)


def count_chunk_tokens(texts: list[str], *, counter: TokenCounter | None = None) -> int:
    """Sum token counts across many texts."""
    c = counter or _DEFAULT
    return sum(c.count(t) for t in texts)


__all__ = [
    "RegexTokenCounter",
    "TokenCounter",
    "count_chunk_tokens",
    "count_tokens",
    "default_counter",
    "token_spans",
]
