"""Tests for MMR (Maximal Marginal Relevance) diversity reranking."""

from __future__ import annotations

import pytest

from recommendation.mmr import mmr_rerank, similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _poi(name: str, *, score: float = 0.5, tags: list[str] | None = None) -> dict:
    """Create a minimal scored POI dict for testing."""
    return {"name": name, "score": score, "tags": tags or []}


# ---------------------------------------------------------------------------
# Similarity function tests
# ---------------------------------------------------------------------------


class TestSimilarity:
    """Tests for the Jaccard similarity function."""

    def test_identical_tags(self) -> None:
        """Same tag sets should have similarity 1.0."""
        poi_a = _poi("A", tags=["文化", "历史"])
        poi_b = _poi("B", tags=["文化", "历史"])
        assert similarity(poi_a, poi_b) == pytest.approx(1.0)

    def test_disjoint_tags(self) -> None:
        """No overlapping tags should have similarity 0.0."""
        poi_a = _poi("A", tags=["寺庙"])
        poi_b = _poi("B", tags=["博物馆"])
        assert similarity(poi_a, poi_b) == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        """Partial overlap: Jaccard = |intersection| / |union|."""
        poi_a = _poi("A", tags=["文化", "历史"])
        poi_b = _poi("B", tags=["文化", "美食"])
        # intersection = {"文化"}, union = {"文化", "历史", "美食"} → 1/3
        assert similarity(poi_a, poi_b) == pytest.approx(1 / 3)

    def test_both_empty_tags(self) -> None:
        """Both POIs with empty tags should return similarity 0.0."""
        poi_a = _poi("A", tags=[])
        poi_b = _poi("B", tags=[])
        assert similarity(poi_a, poi_b) == pytest.approx(0.0)

    def test_one_empty_tags(self) -> None:
        """One empty tag set should return similarity 0.0."""
        poi_a = _poi("A", tags=["文化"])
        poi_b = _poi("B", tags=[])
        assert similarity(poi_a, poi_b) == pytest.approx(0.0)

    def test_missing_tags_field(self) -> None:
        """POI without 'tags' field should be treated as empty tags."""
        poi_a = {"name": "A", "score": 0.5}
        poi_b = _poi("B", tags=["文化"])
        assert similarity(poi_a, poi_b) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# MMR rerank tests
# ---------------------------------------------------------------------------


class TestMMRRerank:
    """Tests for the mmr_rerank function."""

    def test_mmr_selects_diverse_categories(self) -> None:
        """8 temples (high score) + 2 museums (slightly lower).

        With lambda=0.7, MMR should pick some museums for diversity
        rather than filling the entire selection with temples.
        """
        pois: list[dict] = []
        for i in range(8):
            pois.append(_poi(f"Temple_{i}", score=0.9, tags=["寺庙", "文化"]))
        for i in range(2):
            pois.append(_poi(f"Museum_{i}", score=0.85, tags=["博物馆", "文化"]))

        result = mmr_rerank(pois, lambda_=0.7, k=5)

        assert len(result) == 5
        museum_count = sum(1 for p in result if p["name"].startswith("Museum"))
        # MMR should value diversity and pick at least one museum
        assert museum_count >= 1, (
            f"Expected at least 1 museum for diversity, got {museum_count}"
        )

    def test_mmr_respects_lambda_zero(self) -> None:
        """lambda=0 → pure diversity selection.

        After first pick, subsequent picks should maximize diversity
        (minimum similarity to already selected), ignoring score differences.
        """
        pois = [
            _poi("Top1", score=0.99, tags=["寺庙"]),
            _poi("Top2", score=0.98, tags=["寺庙"]),
            _poi("Low1", score=0.10, tags=["博物馆"]),
            _poi("Low2", score=0.09, tags=["美食"]),
            _poi("Low3", score=0.08, tags=["购物"]),
        ]

        result = mmr_rerank(pois, lambda_=0.0, k=3)

        assert len(result) == 3
        # With pure diversity, after first pick, should prefer different categories
        # At least 2 distinct tag groups should appear (not all 寺庙)
        tag_sets = [frozenset(p["tags"]) for p in result]
        unique_tag_sets = set(tag_sets)
        assert len(unique_tag_sets) >= 2, (
            "Pure diversity (lambda=0) should select items with different tags"
        )

    def test_mmr_respects_lambda_one(self) -> None:
        """lambda=1 → pure relevance (just pick top-k by score)."""
        pois = [
            _poi("A", score=0.9, tags=["寺庙"]),
            _poi("B", score=0.8, tags=["寺庙"]),
            _poi("C", score=0.7, tags=["寺庙"]),
            _poi("D", score=0.3, tags=["博物馆"]),
            _poi("E", score=0.1, tags=["博物馆"]),
        ]

        result = mmr_rerank(pois, lambda_=1.0, k=3)

        assert len(result) == 3
        names = [p["name"] for p in result]
        # Should pick top 3 by score regardless of diversity
        assert names == ["A", "B", "C"]

    def test_empty_pois_returns_empty(self) -> None:
        """Empty input should return empty list."""
        assert mmr_rerank([], lambda_=0.7, k=10) == []

    def test_k_greater_than_pois_count(self) -> None:
        """k > len(pois) should return all POIs, not crash."""
        pois = [
            _poi("A", score=0.9, tags=["寺庙"]),
            _poi("B", score=0.8, tags=["博物馆"]),
        ]

        result = mmr_rerank(pois, lambda_=0.7, k=10)

        assert len(result) == 2

    def test_k_zero_returns_empty(self) -> None:
        """k=0 should return empty list."""
        pois = [_poi("A", score=0.9, tags=["寺庙"])]
        assert mmr_rerank(pois, lambda_=0.7, k=0) == []

    def test_all_same_category(self) -> None:
        """All POIs with identical tags should not crash, returns by score order."""
        pois = [
            _poi("A", score=0.9, tags=["寺庙"]),
            _poi("B", score=0.8, tags=["寺庙"]),
            _poi("C", score=0.7, tags=["寺庙"]),
        ]

        result = mmr_rerank(pois, lambda_=0.7, k=2)

        assert len(result) == 2
        # With all same tags, similarity = 1.0, diversity term is constant
        # So effectively picks by highest score
        names = [p["name"] for p in result]
        assert names == ["A", "B"]

    def test_preserves_original_poi_dicts(self) -> None:
        """Result should contain original POI dict references, not copies."""
        poi_a = _poi("A", score=0.9, tags=["寺庙"])
        poi_b = _poi("B", score=0.8, tags=["博物馆"])
        pois = [poi_a, poi_b]

        result = mmr_rerank(pois, lambda_=0.7, k=2)

        # Each returned item should be the same object as the input
        for p in result:
            assert p in pois, "MMR should return original POI dicts, not copies"

    def test_default_parameters(self) -> None:
        """Default lambda=0.7 and k=10 should work without explicit args."""
        pois = [_poi(f"P{i}", score=0.5 + i * 0.01, tags=[f"tag{i}"]) for i in range(5)]

        result = mmr_rerank(pois)

        assert len(result) == 5
