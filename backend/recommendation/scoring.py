"""Multi-factor POI scoring — pure function, no I/O.

Scoring factors (each normalized to [0, 1]):
- preference_score: Jaccard similarity between POI tags and user preferences.
- distance_score: Inverse haversine distance from center, capped at 20 km.
- rating_score: POI rating / 5.0.
- time_score: Default 0.8 placeholder for opening hours.
- popularity_score: review_count / max_review_count.

Total score = weighted sum using caller-supplied weights dict.
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """Compute haversine distance in km between two WGS84 points."""
    r = 6371.0  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Factor scorers
# ---------------------------------------------------------------------------


def _preference_score(poi_tags: set[str], user_prefs: set[str]) -> float:
    """Jaccard similarity between POI tags and user preferences.

    Returns 0.0 when both sets are empty.
    """
    if not poi_tags and not user_prefs:
        return 0.0
    union = poi_tags | user_prefs
    if not union:
        return 0.0
    return len(poi_tags & user_prefs) / len(union)


def _distance_score(
    poi_lng: float,
    poi_lat: float,
    center_lng: float | None,
    center_lat: float | None,
) -> float:
    """Inverse distance score: max(0, 1 - dist/20).

    Returns 0.5 (neutral) when center is None.
    """
    if center_lng is None or center_lat is None:
        return 0.5
    dist = _haversine_km(poi_lng, poi_lat, center_lng, center_lat)
    return max(0.0, 1.0 - dist / 20.0)


def _rating_score(rating: float | None) -> float:
    """Normalize rating to [0, 1]. None → 0.0."""
    if rating is None:
        return 0.0
    return min(rating / 5.0, 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_pois(
    pois: list[dict],
    preferences: list[str],
    weights: dict[str, float],
    center_lng: float | None = None,
    center_lat: float | None = None,
) -> list[dict]:
    """Score POIs using multi-factor weighted scoring.

    Args:
        pois: List of POI dicts with 'tags', 'rating', 'review_count', 'lng', 'lat'.
        preferences: User preference tags (e.g. ['文化', '历史']).
        weights: Dict mapping factor name → weight. Keys:
            'preference', 'distance', 'rating', 'time', 'popularity'.
        center_lng: Optional center longitude for distance scoring.
        center_lat: Optional center latitude for distance scoring.

    Returns:
        New list of POI dicts with added 'score' field, sorted descending.
        Original dicts are not mutated.
    """
    if not pois:
        return []

    pref_set = set(preferences)

    # Max review count for popularity normalization
    max_review = max(
        (poi.get("review_count", 0) for poi in pois),
        default=0,
    )

    scored: list[dict[str, Any]] = []
    for poi in pois:
        poi_tags = set(poi.get("tags", []))
        poi_lng = poi.get("lng", 0.0)
        poi_lat = poi.get("lat", 0.0)
        rating = poi.get("rating")
        review_count = poi.get("review_count", 0)

        factors: dict[str, float] = {
            "preference": _preference_score(poi_tags, pref_set),
            "distance": _distance_score(poi_lng, poi_lat, center_lng, center_lat),
            "rating": _rating_score(rating),
            "time": 0.8,
            "popularity": (review_count / max_review) if max_review > 0 else 0.0,
        }

        total = sum(weights.get(factor, 0.0) * score for factor, score in factors.items())

        scored.append({**poi, "score": total})

    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored
