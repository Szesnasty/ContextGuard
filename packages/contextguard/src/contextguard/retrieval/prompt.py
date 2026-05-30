"""Grounded prompt builder with citations (Milestone B1.5, ADR-014).

Pure and zero-infra (no model, no network): turns a query plus retrieved chunks
into chat messages the LLM gateway can send. Each chunk is wrapped in clear
delimiters and given a numbered citation marker ``[n]`` that maps back to its
``chunk_id``, so the model's answer can be traced to its sources - and so the
leak demo can show *which* confidential chunk the model repeated.

The system instruction pins the model to the provided context only ("answer only
from the context; if it is not there, say you don't know"), which both improves
grounding and removes the fabrication path when no chunks are retrieved.

The delimiters are anti-spoofing discipline: even though phase 2 retrieval is
deliberately naive, fencing each chunk keeps a malicious chunk's text from being
read as instructions, so the leak we demonstrate is the *retrieval* leak, not a
prompt-injection artefact.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from contextguard.llm.gateway import Message

_SYSTEM_INSTRUCTION = (
    "You are a careful assistant. Answer the user's question using ONLY the "
    "context provided below. Cite the sources you use with their bracketed "
    "numbers, e.g. [1]. If the answer is not contained in the context, say you "
    "do not know - do not invent facts."
)

_NO_CONTEXT_INSTRUCTION = (
    "You are a careful assistant. No context was retrieved for this question. "
    "Tell the user you do not have enough information to answer - do not invent "
    "facts."
)

_CHUNK_OPEN = "<<<CHUNK {n} (id={chunk_id})>>>"
_CHUNK_CLOSE = "<<<END CHUNK {n}>>>"


@runtime_checkable
class PromptChunk(Protocol):
    """The minimal shape the prompt builder needs from a retrieved chunk."""

    @property
    def id(self) -> str: ...

    @property
    def text(self) -> str: ...


def build_prompt(query: str, chunks: Sequence[PromptChunk]) -> list[Message]:
    """Build cited chat messages from ``query`` and retrieved ``chunks``.

    Returns OpenAI/LiteLLM-shaped messages: a system message (context-only
    instruction) and a user message embedding each chunk in delimiters with a
    ``[n]`` citation marker. With no chunks, the system message switches to the
    no-context instruction so the model cannot fabricate.
    """
    if not chunks:
        return [
            {"role": "system", "content": _NO_CONTEXT_INSTRUCTION},
            {"role": "user", "content": query},
        ]

    blocks: list[str] = []
    for n, chunk in enumerate(chunks, start=1):
        blocks.append(
            "\n".join(
                (
                    _CHUNK_OPEN.format(n=n, chunk_id=chunk.id),
                    f"[{n}] {chunk.text}",
                    _CHUNK_CLOSE.format(n=n),
                )
            )
        )
    context = "\n\n".join(blocks)
    user_content = f"Context:\n{context}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": _SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_content},
    ]


def citation_map(chunks: Sequence[PromptChunk]) -> dict[int, str]:
    """Map each citation number ``[n]`` to the chunk id it references."""
    return {n: chunk.id for n, chunk in enumerate(chunks, start=1)}


__all__ = ["PromptChunk", "build_prompt", "citation_map"]
