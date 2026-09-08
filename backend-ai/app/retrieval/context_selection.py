"""Context selection (US-018): pick the best, non-redundant chunks.

After reranking sorts candidates by relevance, this makes the final
cut: take the top-scoring ones up to ``final_k``, skipping any
candidate whose dense-vector cosine similarity to an already-selected
chunk exceeds the redundancy threshold. A simplified greedy MMR
(Maximal Marginal Relevance) — relevance-first ordering, diversity
enforced as a hard cutoff rather than a weighted tradeoff.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Candidate:
    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int
    text: str
    dense_vector: list[float]
    fusion_score: float
    rerank_score: float = field(default=0.0)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def select(
    candidates: list[Candidate],
    *,
    final_k: int,
    dedup_threshold: float,
) -> list[Candidate]:
    ranked = sorted(candidates, key=lambda c: c.rerank_score, reverse=True)
    selected: list[Candidate] = []
    for candidate in ranked:
        if len(selected) >= final_k:
            break
        is_redundant = any(
            _cosine_similarity(candidate.dense_vector, chosen.dense_vector) > dedup_threshold
            for chosen in selected
        )
        if is_redundant:
            continue
        selected.append(candidate)
    return selected
