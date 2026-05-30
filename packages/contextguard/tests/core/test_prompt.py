"""Grounded prompt builder tests (Milestone B1.5). Pure, zero-infra."""

from __future__ import annotations

from dataclasses import dataclass

from contextguard.retrieval.prompt import build_prompt, citation_map


@dataclass(frozen=True)
class _Chunk:
    id: str
    text: str


_CHUNKS = [
    _Chunk("acme-mna-falcon#1", "Project Falcon targets a Q3 acquisition."),
    _Chunk("acme-handbook#4", "Expense reports are due monthly."),
]


def test_every_chunk_appears_with_citation_marker() -> None:
    messages = build_prompt("What is Project Falcon?", _CHUNKS)
    user = messages[-1]["content"]
    assert "[1]" in user
    assert "[2]" in user
    assert "Project Falcon targets a Q3 acquisition." in user
    assert "Expense reports are due monthly." in user


def test_citation_markers_reference_real_chunk_ids() -> None:
    messages = build_prompt("q", _CHUNKS)
    user = messages[-1]["content"]
    mapping = citation_map(_CHUNKS)
    assert mapping == {1: "acme-mna-falcon#1", 2: "acme-handbook#4"}
    # The chunk ids are present in the prompt next to their markers.
    for chunk in _CHUNKS:
        assert chunk.id in user


def test_system_instruction_pins_to_context() -> None:
    messages = build_prompt("q", _CHUNKS)
    system = messages[0]
    assert system["role"] == "system"
    assert "ONLY" in system["content"]
    assert "do not know" in system["content"]


def test_chunks_are_fenced_with_delimiters() -> None:
    messages = build_prompt("q", _CHUNKS)
    user = messages[-1]["content"]
    assert "<<<CHUNK 1" in user
    assert "<<<END CHUNK 1>>>" in user


def test_empty_chunks_uses_no_context_instruction() -> None:
    messages = build_prompt("anything", [])
    system = messages[0]
    assert "No context" in system["content"]
    assert "do not invent" in system["content"]
    # The question still reaches the model, but with no fabricated context.
    assert messages[-1]["content"] == "anything"


def test_messages_are_openai_shaped() -> None:
    messages = build_prompt("q", _CHUNKS)
    assert all(set(m.keys()) == {"role", "content"} for m in messages)
    assert [m["role"] for m in messages] == ["system", "user"]
