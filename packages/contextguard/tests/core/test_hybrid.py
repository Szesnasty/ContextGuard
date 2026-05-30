"""Hybrid rank-fusion tests (Milestone B1.4, ADR-001). Pure functions, zero-infra."""

from __future__ import annotations

import math

import pytest
from contextguard.retrieval.hybrid import reciprocal_rank_fusion


def test_alpha_one_is_pure_dense_order() -> None:
    dense = ["a", "b", "c"]
    keyword = ["c", "b", "a"]
    fused = reciprocal_rank_fusion(dense, keyword, alpha=1.0, k=3)
    assert [chunk_id for chunk_id, _ in fused] == dense


def test_alpha_zero_is_pure_keyword_order() -> None:
    dense = ["a", "b", "c"]
    keyword = ["c", "b", "a"]
    fused = reciprocal_rank_fusion(dense, keyword, alpha=0.0, k=3)
    assert [chunk_id for chunk_id, _ in fused] == keyword


def test_chunk_in_both_appears_once_with_summed_score() -> None:
    dense = ["x", "y"]
    keyword = ["x", "z"]
    fused = reciprocal_rank_fusion(dense, keyword, alpha=0.5, k=10)
    ids = [chunk_id for chunk_id, _ in fused]
    assert ids.count("x") == 1  # deduplicated
    scores = dict(fused)
    # x is rank 1 in both lists; its fused score must beat single-list y and z.
    assert scores["x"] > scores["y"]
    assert scores["x"] > scores["z"]


def test_scores_are_finite_and_non_negative() -> None:
    fused = reciprocal_rank_fusion(["a", "b"], ["b", "c"], alpha=0.5, k=10)
    for _, score in fused:
        assert math.isfinite(score)
        assert score >= 0


def test_k_bounds_result() -> None:
    fused = reciprocal_rank_fusion(["a", "b", "c", "d"], ["d", "c", "b", "a"], k=2)
    assert len(fused) == 2


def test_empty_inputs_return_empty() -> None:
    assert reciprocal_rank_fusion([], [], k=5) == []


def test_alpha_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(["a"], ["a"], alpha=1.5)
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(["a"], ["a"], alpha=-0.1)
