"""FixedSizeChunker tests (Milestone B1.2, build plan step 02-baseline-rag/02).

Pure, zero-infra: no DB, no network. Covers determinism, overlap, size bound,
metadata inheritance, stable ids, and small/empty edge cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import pytest
from contextguard.core.tokens import count_tokens
from contextguard.core.types import Classification
from contextguard.retrieval import FixedSizeChunker, chunk_corpus


@dataclass(frozen=True)
class _Doc:
    doc_id: str
    tenant: str
    classification: Classification
    text: str


def _doc(text: str, *, doc_id: str = "d1") -> _Doc:
    return _Doc(doc_id=doc_id, tenant="acme", classification=Classification.CONFIDENTIAL, text=text)


_LONG = " ".join(f"word{i}" for i in range(120))


def test_chunker_deterministic() -> None:
    doc = _doc(_LONG)
    a = FixedSizeChunker(size_tokens=20, overlap_tokens=5).chunk(doc)
    b = FixedSizeChunker(size_tokens=20, overlap_tokens=5).chunk(doc)
    assert [(c.id, c.text, c.metadata) for c in a] == [(c.id, c.text, c.metadata) for c in b]


def test_chunk_overlap() -> None:
    """Consecutive chunks share the configured number of overlap tokens."""
    chunker = FixedSizeChunker(size_tokens=20, overlap_tokens=5)
    chunks = chunker.chunk(_doc(_LONG))
    assert len(chunks) >= 2
    for prev, nxt in pairwise(chunks):
        prev_tail = prev.text.split()[-5:]
        nxt_head = nxt.text.split()[:5]
        assert prev_tail == nxt_head


def test_chunk_size_bound() -> None:
    """No chunk exceeds size_tokens tokens."""
    chunker = FixedSizeChunker(size_tokens=20, overlap_tokens=5)
    for c in chunker.chunk(_doc(_LONG)):
        assert count_tokens(c.text) <= 20
        assert int(c.metadata["token_count"]) <= 20


def test_metadata_inheritance() -> None:
    """Every chunk carries the document's tenant + classification + doc_id."""
    doc = _doc(_LONG, doc_id="acme-secret")
    for c in FixedSizeChunker(size_tokens=20, overlap_tokens=5).chunk(doc):
        assert c.doc_id == "acme-secret"
        assert c.tenant == "acme"
        assert c.classification is Classification.CONFIDENTIAL


def test_chunk_ids_stable_and_unique() -> None:
    doc = _doc(_LONG)
    ids = [c.id for c in FixedSizeChunker(size_tokens=20, overlap_tokens=5).chunk(doc)]
    assert len(ids) == len(set(ids))  # unique within a document
    again = [c.id for c in FixedSizeChunker(size_tokens=20, overlap_tokens=5).chunk(doc)]
    assert ids == again  # stable across runs


def test_small_doc_yields_one_chunk() -> None:
    chunks = FixedSizeChunker(size_tokens=500, overlap_tokens=50).chunk(
        _doc("just a short sentence")
    )
    assert len(chunks) == 1
    assert chunks[0].text == "just a short sentence"


def test_empty_doc_yields_no_chunks() -> None:
    assert FixedSizeChunker().chunk(_doc("")) == []
    assert FixedSizeChunker().chunk(_doc("   \n  ")) == []


def test_full_coverage_first_and_last_token() -> None:
    """The chunks together cover the whole document from first to last token."""
    doc = _doc(_LONG)
    chunks = FixedSizeChunker(size_tokens=20, overlap_tokens=5).chunk(doc)
    assert chunks[0].text.startswith("word0")
    assert chunks[-1].text.rstrip().endswith("word119")


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError):
        FixedSizeChunker(size_tokens=0)
    with pytest.raises(ValueError):
        FixedSizeChunker(size_tokens=10, overlap_tokens=10)


def test_chunks_seed_corpus_inheriting_classification() -> None:
    """Integration with the real loader: chunks inherit each doc's classification.

    This is the step-2.2 'loader maps classification onto chunks' check, using
    the zero-infra seed-corpus loader from the eval-harness. Skipped in the
    minimum-deps tier where the eval-harness package is absent.
    """
    pytest.importorskip("contextguard_eval_harness.corpus")
    from contextguard_eval_harness.corpus import load_corpus

    docs = load_corpus()
    chunks = chunk_corpus(docs, FixedSizeChunker())  # type: ignore[arg-type]
    assert chunks
    by_doc = {d.doc_id: d for d in docs}
    for c in chunks:
        assert c.classification is by_doc[c.doc_id].classification
        assert c.tenant == by_doc[c.doc_id].tenant
