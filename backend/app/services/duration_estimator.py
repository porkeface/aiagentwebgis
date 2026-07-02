"""POI visit duration estimation based on category, rating, and Amap metadata.

Used by the planning pipeline to calculate dynamic daily capacity instead of
hardcoded MAX_POI_PER_DAY.  Estimates include buffer time between POIs.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Category → base visit duration (minutes)
# Sourced from 圆周旅迹 reference patterns and general tourism guidelines.
# Ordered from longest to shortest typical visit.
# ---------------------------------------------------------------------------

CATEGORY_DURATION_MAP: dict[str, int] = {
    # Large scenic areas — half-day visits
    "风景名胜": 180,
    "国家级景点": 180,
    "世界遗产": 180,
    "纪念馆": 60,
    "寺庙道观": 90,
    "教堂": 45,
    "博物馆": 120,
    "展览馆": 90,
    "美术馆": 90,
    "科技馆": 120,
    "会展中心": 90,

    # Parks & nature
    "公园": 90,
    "城市广场": 30,
    "动物园": 150,
    "植物园": 120,
    "水族馆": 90,
    "游乐园": 240,
    "主题公园": 240,
    "国家级森林公园": 240,
    "海滩": 120,
    "岛屿": 240,
    "温泉": 120,

    # Cultural & historic
    "文化街区": 150,
    "历史遗址": 90,
    "古村镇": 180,
    "特色街区": 90,
    "创意园区": 60,

    # Shopping & food
    "购物中心": 90,
    "商业步行街": 120,
    "夜市": 60,
    "美食街": 90,
    "特色餐厅": 60,

    # Entertainment & nightlife
    "电影院": 120,
    "剧院": 120,
    "音乐厅": 120,
    "夜游": 60,
    "游船": 60,
    "观景台": 45,
    "缆车": 30,

    # Sports & outdoor
    "运动场馆": 90,
    "滑雪场": 240,
    "高尔夫球场": 180,
    "登山": 240,
    "徒步路线": 240,

    # Transportation hubs (not usually POIs but may appear)
    "机场": 30,
    "火车站": 15,
    "汽车站": 10,
    "港口码头": 15,

    # Fallback for unknown categories
    "default": 90,
}

# ---------------------------------------------------------------------------
# Adjustment multipliers
# ---------------------------------------------------------------------------

IMPORTANCE_MULTIPLIER: dict[str, float] = {
    "5A": 1.3,
    "4A": 1.15,
    "3A": 1.0,
    "2A": 0.85,
    "A": 0.7,
}


def estimate_visit_duration(
    category: str | None = None,
    rating: float | None = None,
    importance: str | None = None,
    review_count: int | None = None,
) -> int:
    """Estimate how many minutes a visitor should spend at a POI.

    Estimation is based on:
    1. Category → base duration from CATEGORY_DURATION_MAP
    2. Importance label (5A/4A/3A) → multiplier
    3. Rating → slight boost for very high-rated spots
    4. Review count → slight boost for very popular spots

    Returns:
        Estimated minutes as an integer (range: ~10–360).
    """
    base = CATEGORY_DURATION_MAP.get("default", 90)

    if category:
        # Try exact match first, then check if any key is a substring
        if category in CATEGORY_DURATION_MAP:
            base = CATEGORY_DURATION_MAP[category]
        else:
            for key, dur in CATEGORY_DURATION_MAP.items():
                if key in category:
                    base = dur
                    break

    multiplier = 1.0

    # Importance adjustment (5A/4A etc.)
    if importance:
        clean = importance.strip().upper()
        for label, mult in IMPORTANCE_MULTIPLIER.items():
            if label in clean:
                multiplier = mult
                break

    # Rating boost: very high-rated spots get +10%
    if rating is not None and rating >= 4.5:
        multiplier *= 1.1

    # Popularity boost: very popular spots (>1000 reviews) get +10%
    if review_count is not None and review_count > 1000:
        multiplier *= 1.1

    # Cap at reasonable bounds
    estimated = int(base * multiplier)
    return min(max(estimated, 15), 360)


def estimate_daily_capacity(
    poi_durations: list[int],
    avg_commute_min: int = 20,
    meal_break_min: int = 60,
    max_day_min: int = 660,  # 11h active time (8am–7pm)
) -> int:
    """Calculate how many POIs can fit in a day given their durations + overhead.

    Args:
        poi_durations: Estimated visit durations for candidate POIs (minutes),
            sorted by priority (highest first).
        avg_commute_min: Average commute time between consecutive POIs.
        meal_break_min: Time reserved for lunch/dinner.
        max_day_min: Maximum active time per day (default 11 hours).

    Returns:
        Number of POIs that fit within the daily budget.
    """
    available = max_day_min - meal_break_min  # reserve meal time
    count = 0
    total = 0

    for dur in poi_durations:
        needed = dur + (avg_commute_min if count > 0 else 0)
        if total + needed > available:
            break
        total += needed
        count += 1

    return max(count, 2)  # at least 2 POIs per day


def estimate_poi_duration_from_dict(poi: dict) -> int:
    """Convenience wrapper that extracts fields from a POI dict.

    Handles both Amap raw POIs and our normalized POI dicts.
    """
    return estimate_visit_duration(
        category=poi.get("category") or poi.get("type"),
        rating=poi.get("rating"),
        importance=poi.get("importance"),
        review_count=poi.get("review_count"),
    )
