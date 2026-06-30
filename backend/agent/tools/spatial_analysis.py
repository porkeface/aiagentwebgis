"""Multi-factor POI scoring tool — pure computation, no API calls.

Scoring factors and weights (MVP):
- preference_score (0.30): Jaccard similarity between POI tags and user prefs.
- distance_score (0.20): Inverse distance from city center, normalized to [0, 1].
- rating_score (0.20): POI rating / 5.0.
- time_score (0.15): Placeholder — always 1.0 for MVP.
- popularity_score (0.15): review_count / max_review_count, normalized.
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "preference": 0.30,
    "distance": 0.20,
    "rating": 0.20,
    "time": 0.15,
    "popularity": 0.15,
}


# ---------------------------------------------------------------------------
# Internal scoring helpers
# ---------------------------------------------------------------------------


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 0.0
    intersection = a & b
    union = a | b
    if not union:
        return 0.0
    return len(intersection) / len(union)


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


def _compute_scores(
    pois: list[dict[str, Any]],
    preferences: list[str],
    city_center_lng: float | None = None,
    city_center_lat: float | None = None,
) -> list[dict[str, float]]:
    """Compute per-factor scores for each POI.

    Returns list of dicts with keys:
        preference_score, distance_score, rating_score, time_score,
        popularity_score.
    """
    if not pois:
        return []

    pref_set = set(preferences)

    # Max review count for popularity normalization
    max_review = max(
        (poi.get("review_count") or 0 for poi in pois),
        default=1,
    )
    if max_review == 0:
        max_review = 1  # avoid division by zero

    # Max distance for distance normalization
    if city_center_lng is not None and city_center_lat is not None:
        distances = [
            _haversine_km(
                poi.get("lng", 0.0),
                poi.get("lat", 0.0),
                city_center_lng,
                city_center_lat,
            )
            for poi in pois
        ]
        max_dist = max(distances) if distances else 1.0
        if max_dist == 0:
            max_dist = 1.0
    else:
        distances = None
        max_dist = 1.0

    scores: list[dict[str, float]] = []
    for i, poi in enumerate(pois):
        # preference_score — Jaccard similarity
        poi_tags = set(poi.get("tags", []))
        preference_score = _jaccard_similarity(pref_set, poi_tags)

        # distance_score — inverse distance from city center
        if distances is not None:
            distance_score = 1.0 - (distances[i] / max_dist)
        else:
            distance_score = 0.5  # neutral when no city center given

        # rating_score — normalized to [0, 1]
        rating = poi.get("rating") or 0.0
        rating_score = min(rating / 5.0, 1.0) if rating else 0.0

        # time_score — placeholder
        time_score = 1.0

        # popularity_score — normalized by max review count
        review_count = poi.get("review_count") or 0
        popularity_score = review_count / max_review

        scores.append(
            {
                "preference_score": preference_score,
                "distance_score": distance_score,
                "rating_score": rating_score,
                "time_score": time_score,
                "popularity_score": popularity_score,
            }
        )

    return scores


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------


def score_pois_tool(
    pois: list[dict[str, Any]],
    preferences: list[str],
    city_center_lng: float | None = None,
    city_center_lat: float | None = None,
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Score POIs using multi-factor weighted scoring.

    Args:
        pois: List of POI dicts with 'tags', 'rating', 'review_count', etc.
        preferences: User preference tags (e.g. ['文化', '历史']).
        city_center_lng: Optional city center longitude for distance scoring.
        city_center_lat: Optional city center latitude for distance scoring.
        weights: Optional weight overrides per factor. Falls back to
            module-level WEIGHTS for any missing keys.

    Returns:
        Copy of POI list with added 'score' field (weighted sum in [0, 1]).
    """
    if not pois:
        return []

    effective_weights = {**WEIGHTS}
    if weights:
        effective_weights.update(weights)

    per_factor = _compute_scores(
        pois=pois,
        preferences=preferences,
        city_center_lng=city_center_lng,
        city_center_lat=city_center_lat,
    )

    result: list[dict[str, Any]] = []
    for poi, sc in zip(pois, per_factor):
        weighted = (
            effective_weights.get("preference", 0) * sc["preference_score"]
            + effective_weights.get("distance", 0) * sc["distance_score"]
            + effective_weights.get("rating", 0) * sc["rating_score"]
            + effective_weights.get("time", 0) * sc["time_score"]
            + effective_weights.get("popularity", 0) * sc["popularity_score"]
        )
        scored_poi = {**poi, "score": round(weighted, 4)}
        result.append(scored_poi)

    return result
