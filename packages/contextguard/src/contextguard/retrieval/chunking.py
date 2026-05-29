"""Deterministic chunking behind a swappable interface (Milestone B1.2, ADR-007).

The default :class:`FixedSizeChunker` slices a document into fixed-size,
overlapping token windows. It is **pure and zero-infra** (it depends only on the
core token utilities and the domain types), so it runs in the core test tier
with no DB or network.

Every emitted :class:`Chunk` *inherits* ``doc_id``, ``tenant`` and
``classification`` from its source document. ContextGuard enforces this metadata
later (ADR-005); it never invents it — so the chunker is where the document's
sensitivity is carried onto the unit the policy will actually see.

Chunk ids are a stable hash of ``(doc_id, start_offset)`` so re-running the
chunker over the same corpus yields byte-identical ids — a prerequisite for
deterministic embedding and replay.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from contextguard.core.tokens import token_spans
from contextguard.core.types import Chunk, Classification


@runtime_checkable
class SourceDocument(Protocol):
    """The minimal shape a chunker needs from a document (structural typing).

    The seed-corpus ``Document`` (eval-harness) satisfies this protocol as-is, so
    loaded documents flow into the chunker without the library depending on the
    loader.
    """

    @property
    def doc_id(self) -> str: ...
    @property
    def tenant(self) -> str: ...
    @property
    def classification(self) -> Classification: ...
    @property
    def text(self) -> str: ...


@runtime_checkable
class Chunker(Protocol):
    """Turns one document into an ordered list of chunks."""

    def chunk(self, document: SourceDocument) -> list[Chunk]: ...


def _chunk_id(doc_id: str, start_offset: int) -> str:
    """Stable, collision-resistant id for a chunk at a given start offset."""
    digest = hashlib.sha1(f"{doc_id}:{start_offset}".encode()).hexdigest()  # noqa: S324 - id, not security
    return f"{doc_id}#{digest[:12]}"


class FixedSizeChunker:
    """Fixed-size token windows with overlap (ADR-007 default: 500 / 50).

    The document text is tokenized once; consecutive windows of ``size_tokens``
    tokens advance by ``size_tokens - overlap_tokens`` and share ``overlap_tokens``
    tokens with their predecessor. Each chunk's text is sliced from the original
    string between the first and last token offsets in its window, so the
    original whitespace is preserved and offsets stay meaningful.
    """

    def __init__(self, size_tokens: int = 500, overlap_tokens: int = 50) -> None:
        if size_tokens <= 0:
            raise ValueError("size_tokens must be positive")
        if not 0 <= overlap_tokens < size_tokens:
            raise ValueError("overlap_tokens must be in [0, size_tokens)")
        self.size_tokens = size_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, document: SourceDocument) -> list[Chunk]:
        spans = token_spans(document.text)
        if not spans:
            return []

        step = self.size_tokens - self.overlap_tokens
        chunks: list[Chunk] = []
        for index, window_start in enumerate(range(0, len(spans), step)):
            window = spans[window_start : window_start + self.size_tokens]
            char_start = window[0][0]
            char_end = window[-1][1]
            text = document.text[char_start:char_end]
            chunks.append(
                Chunk(
                    id=_chunk_id(document.doc_id, char_start),
                    doc_id=document.doc_id,
                    tenant=document.tenant,
                    classification=document.classification,
                    text=text,
                    metadata={
                        "chunk_index": str(index),
                        "char_start": str(char_start),
                        "char_end": str(char_end),
                        "token_count": str(len(window)),
                    },
                )
            )
            # The final window reaches the end of the document; stop so we do not
            # emit a trailing chunk that is wholly contained in the previous one.
            if window_start + self.size_tokens >= len(spans):
                break
        return chunks


def chunk_corpus(documents: list[SourceDocument], chunker: Chunker) -> list[Chunk]:
    """Chunk many documents in order, flattening the result."""
    out: list[Chunk] = []
    for document in documents:
        out.extend(chunker.chunk(document))
    return out


__all__ = ["Chunker", "FixedSizeChunker", "SourceDocument", "chunk_corpus"]
