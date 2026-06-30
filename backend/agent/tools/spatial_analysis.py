"""Multi-factor POI scoring tool — wrapped for LangChain ReAct agent.

Scores POIs on preference match, distance, rating, and popularity.
"""

from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool


WEIGHTS: dict[str, float] = {
    "preference": 0.30,
    "distance": 0.20,
    "rating": 0.20,
    "time": 0.15,
    "popularity": 0.15,
}


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """Compute haversine distance in km between two WGS84 points."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 0.0
    intersection = a & b
    union = a | b
    if not union:
        return 0.0
    return len(intersection) / len(union)


@tool
async def score_pois(
    pois: list[dict[str, Any]],
    preferences: list[str],
    city_center_lng: float = 0.0,
    city_center_lat: float = 0.0,
) -> list[dict[str, Any]]:
    """对 POI 列表进行多维度打分排序。

    综合偏好匹配度、距离市中心距离、评分、热度等因素对 POI 进行评分。
    返回带 score 字段的 POI 列表，按得分降序排列。

    在从搜索结果中选择 POI 时很有用——可以先打分再按得分挑选。

    Args:
        pois: POI 列表，每个需有 tags、rating、review_count、lng、lat 字段
        preferences: 用户偏好标签列表，如 ["文化", "美食"]
        city_center_lng: 城市中心经度（用于距离打分），不传则距离分取中性值
        city_center_lat: 城市中心纬度
    """
    if not pois:
        return []

    pref_set = set(preferences)

    max_review = max(
        (poi.get("review_count") or 0 for poi in pois),
        default=1,
    )
    if max_review == 0:
        max_review = 1

    if city_center_lng and city_center_lat:
        distances = [
            _haversine_km(poi.get("lng", 0.0), poi.get("lat", 0.0), city_center_lng, city_center_lat)
            for poi in pois
        ]
        max_dist = max(distances) if distances else 1.0
        if max_dist == 0:
            max_dist = 1.0
    else:
        distances = None
        max_dist = 1.0

    result: list[dict[str, Any]] = []
    for i, poi in enumerate(pois):
        poi_tags = set(poi.get("tags", []))
        preference_score = _jaccard_similarity(pref_set, poi_tags)

        if distances is not None:
            distance_score = 1.0 - (distances[i] / max_dist)
        else:
            distance_score = 0.5

        rating = poi.get("rating") or 0.0
        rating_score = min(rating / 5.0, 1.0) if rating else 0.0

        review_count = poi.get("review_count") or 0
        popularity_score = review_count / max_review

        weighted = (
            WEIGHTS["preference"] * preference_score
            + WEIGHTS["distance"] * distance_score
            + WEIGHTS["rating"] * rating_score
            + WEIGHTS["time"] * 1.0
            + WEIGHTS["popularity"] * popularity_score
        )

        result.append({**poi, "score": round(weighted, 4)})

    result.sort(key=lambda p: p.get("score", 0), reverse=True)
    return result
