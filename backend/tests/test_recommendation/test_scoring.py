"""Tests for multi-factor POI scoring."""

from __future__ import annotations

import pytest

from recommendation.scoring import score_pois


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "preference": 0.30,
    "distance": 0.20,
    "rating": 0.20,
    "time": 0.15,
    "popularity": 0.15,
}


def _poi(
    name: str = "POI",
    *,
    tags: list[str] | None = None,
    rating: float | None = 4.0,
    review_count: int = 10,
    lng: float = 116.4,
    lat: float = 39.9,
) -> dict:
    """Create a minimal POI dict for testing."""
    return {
        "name": name,
        "tags": tags or [],
        "rating": rating,
        "review_count": review_count,
        "lng": lng,
        "lat": lat,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScorePois:
    """Tests for the score_pois function."""

    def test_scoring_prefers_matching_tags(self) -> None:
        """POI with tags matching user preferences should score higher."""
        prefs = ["文化", "历史", "美食"]

        poi_match = _poi("Match", tags=["文化", "历史"])
        poi_no_match = _poi("NoMatch", tags=["购物", "科技"])

        results = score_pois(
            [poi_no_match, poi_match],
            preferences=prefs,
            weights=DEFAULT_WEIGHTS,
        )

        scored = {p["name"]: p["score"] for p in results}
        assert scored["Match"] > scored["NoMatch"]

    def test_scoring_prefers_closer_pois(self) -> None:
        """Closer POI should score higher on distance factor."""
        center_lng, center_lat = 116.4, 39.9

        poi_near = _poi("Near", lng=116.401, lat=39.901)
        poi_far = _poi("Far", lng=117.0, lat=40.5)

        results = score_pois(
            [poi_far, poi_near],
            preferences=[],
            weights=DEFAULT_WEIGHTS,
            center_lng=center_lng,
            center_lat=center_lat,
        )

        scored = {p["name"]: p["score"] for p in results}
        assert scored["Near"] > scored["Far"]

    def test_scoring_prefers_higher_rated(self) -> None:
        """Higher-rated POI should score higher."""
        poi_high = _poi("High", rating=4.8)
        poi_low = _poi("Low", rating=1.0)

        results = score_pois(
            [poi_low, poi_high],
            preferences=[],
            weights=DEFAULT_WEIGHTS,
        )

        scored = {p["name"]: p["score"] for p in results}
        assert scored["High"] > scored["Low"]

    def test_scoring_sorts_descending(self) -> None:
        """Result list must be sorted by score in descending order."""
        pois = [
            _poi("A", tags=["a"], rating=1.0, review_count=1),
            _poi("B", tags=["b", "c"], rating=4.5, review_count=100),
            _poi("C", tags=["d"], rating=3.0, review_count=50),
        ]

        results = score_pois(
            pois,
            preferences=["b", "c"],
            weights=DEFAULT_WEIGHTS,
        )

        scores = [p["score"] for p in results]
        assert scores == sorted(scores, reverse=True)

    def test_returns_new_dicts(self) -> None:
        """Original POI dicts must not be mutated."""
        poi = _poi("Original", tags=["x"], rating=3.0)
        original_keys = set(poi.keys())

        results = score_pois([poi], preferences=["x"], weights=DEFAULT_WEIGHTS)

        assert "score" not in poi  # original unchanged
        assert "score" in results[0]
        assert set(poi.keys()) == original_keys

    def test_empty_pois_returns_empty(self) -> None:
        """Empty input should return empty list."""
        results = score_pois([], preferences=[], weights=DEFAULT_WEIGHTS)
        assert results == []

    def test_none_rating_scores_zero_for_rating(self) -> None:
        """POI with None rating should get rating_score = 0.0."""
        poi_no_rating = _poi("NoRating", rating=None)
        poi_with_rating = _poi("WithRating", rating=4.0)

        results = score_pois(
            [poi_with_rating, poi_no_rating],
            preferences=[],
            weights={"preference": 0.0, "distance": 0.0, "rating": 1.0, "time": 0.0, "popularity": 0.0},
        )

        scored = {p["name"]: p["score"] for p in results}
        assert scored["WithRating"] > scored["NoRating"]
        assert scored["NoRating"] == pytest.approx(0.0)

    def test_no_center_gives_neutral_distance(self) -> None:
        """Without center coordinates, distance_score should be 0.5 (neutral)."""
        poi = _poi("Test", rating=0.0, review_count=0)

        results = score_pois(
            [poi],
            preferences=[],
            weights={"preference": 0.0, "distance": 1.0, "rating": 0.0, "time": 0.0, "popularity": 0.0},
        )

        assert results[0]["score"] == pytest.approx(0.5)

    def test_both_empty_prefs_and_tags_gives_zero_preference(self) -> None:
        """Both empty preferences and tags should give preference_score = 0.0."""
        poi = _poi("Test", tags=[], rating=0.0, review_count=0)

        results = score_pois(
            [poi],
            preferences=[],
            weights={"preference": 1.0, "distance": 0.0, "rating": 0.0, "time": 0.0, "popularity": 0.0},
        )

        assert results[0]["score"] == pytest.approx(0.0)

    def test_popularity_normalization(self) -> None:
        """Popularity score should be review_count / max_review_count."""
        pois = [
            _poi("Max", review_count=100, rating=0.0, tags=[]),
            _poi("Half", review_count=50, rating=0.0, tags=[]),
            _poi("Zero", review_count=0, rating=0.0, tags=[]),
        ]

        results = score_pois(
            pois,
            preferences=[],
            weights={"preference": 0.0, "distance": 0.0, "rating": 0.0, "time": 0.0, "popularity": 1.0},
        )

        scored = {p["name"]: p["score"] for p in results}
        assert scored["Max"] == pytest.approx(1.0)
        assert scored["Half"] == pytest.approx(0.5)
        assert scored["Zero"] == pytest.approx(0.0)

    def test_distance_beyond_20km_clamps_to_zero(self) -> None:
        """Distance score should clamp to 0.0 beyond 20 km."""
        # ~22 km away from center
        poi_far = _poi("Far", lng=117.0, lat=40.5)
        center_lng, center_lat = 116.4, 39.9

        results = score_pois(
            [poi_far],
            preferences=[],
            weights={"preference": 0.0, "distance": 1.0, "rating": 0.0, "time": 0.0, "popularity": 0.0},
            center_lng=center_lng,
            center_lat=center_lat,
        )

        assert results[0]["score"] == pytest.approx(0.0, abs=0.01)

    def test_time_score_is_0_8(self) -> None:
        """Time score should be 0.8 (default placeholder)."""
        poi = _poi("Test", rating=0.0, review_count=0, tags=[])

        results = score_pois(
            [poi],
            preferences=[],
            weights={"preference": 0.0, "distance": 0.0, "rating": 0.0, "time": 1.0, "popularity": 0.0},
        )

        assert results[0]["score"] == pytest.approx(0.8)
