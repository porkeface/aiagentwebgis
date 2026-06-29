"""Maximal Marginal Relevance (MMR) diversity reranking — pure function, no I/O.

Selects a diverse subset of scored POIs by balancing relevance (score) against
diversity (category similarity via Jaccard overlap).

Reference:
    Carbonell & Goldstein (1998). "The Use of MMR, Diversity-Based Reranking
    for Reordering Documents and Producing Summaries".
"""

from __future__ import annotations

from typing import Any


def similarity(poi_a: dict[str, Any], poi_b: dict[str, Any]) -> float:
    """Jaccard similarity between two POIs based on category tags.

    similarity = |tags_a ∩ tags_b| / |tags_a ∪ tags_b|

    Returns 0.0 when both POIs have no tags.
    """
    tags_a = set(poi_a.get("tags", []))
    tags_b = set(poi_b.get("tags", []))

    if not tags_a and not tags_b:
        return 0.0

    union = tags_a | tags_b
    if not union:
        return 0.0

    return len(tags_a & tags_b) / len(union)


def mmr_rerank(
    pois: list[dict],
    lambda_: float = 0.7,
    k: int = 10,
) -> list[dict]:
    """Select a diverse subset of POIs using Maximal Marginal Relevance.

    At each iteration, selects the POI that maximizes:
        mmr = lambda_ * relevance - (1 - lambda_) * max_similarity_to_selected

    Where:
        - relevance: POI's "score" field (from scoring.py)
        - similarity: Jaccard overlap of category tags
        - max_similarity_to_selected: max similarity to any POI already in
          `selected` (0.0 when selected is empty)

    Args:
        pois: List of POI dicts with "score" and "tags" fields (from scoring.py).
        lambda_: Trade-off parameter in [0, 1].
                 1.0 = pure relevance (no diversity).
                 0.0 = pure diversity (ignore relevance).
        k: Number of POIs to select. Clamped to len(pois) if larger.

    Returns:
        List of selected POI dicts (original references, not copies),
        in selection order.
    """
    if not pois or k <= 0:
        return []

    candidates: list[dict] = list(pois)
    selected: list[dict] = []
    effective_k = min(k, len(pois))

    for _ in range(effective_k):
        best_mmr = float("-inf")
        best_idx = 0

        for idx, candidate in enumerate(candidates):
            relevance = candidate.get("score", 0.0)

            if not selected:
                max_sim = 0.0
            else:
                max_sim = max(
                    similarity(candidate, sel) for sel in selected
                )

            mmr_score = lambda_ * relevance - (1 - lambda_) * max_sim

            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_idx = idx

        chosen = candidates.pop(best_idx)
        selected.append(chosen)

    return selected
