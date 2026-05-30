"""Hybrid merge of dense + keyword rankings (Milestone B1.4, ADR-001).

Dense kNN (ADR-008) and BM25 (``bm25``) score on incomparable scales - L2
distance (lower is better) versus a BM25 relevance score (higher is better).
Min-max normalizing those onto a common range is fragile: it divides by zero
when every score is equal (producing NaNs) and is sensitive to outliers.

Instead the merge uses **weighted Reciprocal Rank Fusion (RRF)**, which depends
only on each item's *rank* within its own list. That sidesteps normalization
entirely (no NaNs, no scale mismatch), naturally deduplicates an item found by
both retrievers, and degrades cleanly at the boundaries: ``alpha=1.0`` is pure
dense order and ``alpha=0.0`` is pure keyword order.
"""

from __future__ import annotations

from collections.abc import Sequence

# RRF damping constant. 60 is the value from the original Cormack et al. paper;
# it flattens the contribution of deep ranks so the top results dominate.
_RRF_C = 60


def reciprocal_rank_fusion(
    dense_ids: Sequence[str],
    keyword_ids: Sequence[str],
    *,
    alpha: float = 0.5,
    k: int = 5,
    c: int = _RRF_C,
) -> list[tuple[str, float]]:
    """Fuse two ranked id lists into one, best first.

    ``dense_ids`` and ``keyword_ids`` are ordered best-first (rank 1 = first).
    ``alpha`` weights the dense side: ``1.0`` => pure dense, ``0.0`` => pure
    keyword. Returns up to ``k`` ``(id, fused_score)`` pairs; ids break ties so
    the order is deterministic. Scores are always finite and non-negative.
    """
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be in [0, 1]")
    if c <= 0:
        raise ValueError("c must be positive")

    fused: dict[str, float] = {}
    for rank, chunk_id in enumerate(dense_ids, start=1):
        fused[chunk_id] = fused.get(chunk_id, 0.0) + alpha * (1.0 / (c + rank))
    for rank, chunk_id in enumerate(keyword_ids, start=1):
        fused[chunk_id] = fused.get(chunk_id, 0.0) + (1 - alpha) * (1.0 / (c + rank))

    ranked = sorted(fused.items(), key=lambda pair: (-pair[1], pair[0]))
    return ranked[: max(k, 0)]


__all__ = ["reciprocal_rank_fusion"]
