"""Token counter tests (step 1.4)."""

from __future__ import annotations

from contextguard.core.tokens import (
    RegexTokenCounter,
    TokenCounter,
    count_chunk_tokens,
    count_tokens,
    default_counter,
)


def test_default_counter_is_token_counter() -> None:
    assert isinstance(default_counter(), TokenCounter)
    assert isinstance(RegexTokenCounter(), TokenCounter)


def test_known_golden_counts() -> None:
    # "hello world" -> 2 word tokens
    assert count_tokens("hello world") == 2
    # punctuation counts standalone: "a, b." -> a , b . = 4
    assert count_tokens("a, b.") == 4
    assert count_tokens("") == 0
    assert count_tokens("   ") == 0


def test_deterministic() -> None:
    text = "The quick brown fox; jumps over 13 lazy dogs!"
    assert count_tokens(text) == count_tokens(text)


def test_count_chunk_tokens_sums() -> None:
    assert count_chunk_tokens(["hello world", "foo"]) == 3
    assert count_chunk_tokens([]) == 0


def test_custom_counter_is_used() -> None:
    class Fixed:
        def count(self, text: str) -> int:
            return 42

    assert count_tokens("anything", counter=Fixed()) == 42
    assert count_chunk_tokens(["a", "b"], counter=Fixed()) == 84
