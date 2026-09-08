"""Tests for context selection (Epic 4 / US-018): best score, no
redundancy, respects the configured final_k.
"""

from __future__ import annotations

from app.retrieval.context_selection import Candidate, select


def _candidate(name: str, vector: list[float], rerank_score: float) -> Candidate:
    return Candidate(
        document_id=f"doc-{name}",
        filename=f"{name}.txt",
        page_number=None,
        chunk_index=0,
        text=f"text for {name}",
        dense_vector=vector,
        fusion_score=0.5,
        rerank_score=rerank_score,
    )


def test_select_keeps_only_higher_scored_of_near_duplicate_pair():
    # Two candidates with (near-)identical vectors are redundant with
    # each other; only the better-reranked one should survive.
    a = _candidate("a", [1.0, 0.0, 0.0], rerank_score=0.9)
    b = _candidate("b", [0.999, 0.001, 0.0], rerank_score=0.5)

    selected = select([a, b], final_k=10, dedup_threshold=0.92)

    assert [c.document_id for c in selected] == ["doc-a"]


def test_select_keeps_distinct_candidates():
    a = _candidate("a", [1.0, 0.0, 0.0], rerank_score=0.9)
    b = _candidate("b", [0.0, 1.0, 0.0], rerank_score=0.8)
    c = _candidate("c", [0.0, 0.0, 1.0], rerank_score=0.7)

    selected = select([a, b, c], final_k=10, dedup_threshold=0.92)

    assert [cand.document_id for cand in selected] == ["doc-a", "doc-b", "doc-c"]


def test_select_respects_final_k():
    # One-hot vectors of length == candidate count are pairwise
    # orthogonal (cosine similarity 0 for every pair), so this
    # exercises the final_k cutoff in isolation from dedup.
    candidates = [
        _candidate(str(i), [1.0 if j == i else 0.0 for j in range(10)], rerank_score=float(10 - i))
        for i in range(10)
    ]

    selected = select(candidates, final_k=3, dedup_threshold=0.92)

    assert len(selected) == 3
    # Highest rerank scores first (candidate 0 scored 10, the highest).
    assert [c.document_id for c in selected] == ["doc-0", "doc-1", "doc-2"]


def test_select_orders_by_rerank_score_not_input_order():
    a = _candidate("a", [1.0, 0.0, 0.0], rerank_score=0.2)
    b = _candidate("b", [0.0, 1.0, 0.0], rerank_score=0.9)

    selected = select([a, b], final_k=10, dedup_threshold=0.92)

    assert [c.document_id for c in selected] == ["doc-b", "doc-a"]
