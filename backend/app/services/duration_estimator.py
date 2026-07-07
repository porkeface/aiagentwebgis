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
    # Large scenic areas — 60-90 min is realistic for a typical tourist
    "风景名胜": 90,
    "国家级景点": 90,
    "世界遗产": 90,
    "纪念馆": 45,
    "寺庙道观": 45,
    "教堂": 30,
    "博物馆": 90,
    "展览馆": 60,
    "美术馆": 60,
    "科技馆": 90,
    "会展中心": 45,

    # Parks & nature
    "公园": 45,
    "城市广场": 20,
    "动物园": 90,
    "植物园": 60,
    "水族馆": 60,
    "游乐园": 150,
    "主题公园": 150,
    "国家级森林公园": 120,
    "海滩": 60,
    "岛屿": 120,
    "温泉": 60,

    # Cultural & historic
    "文化街区": 60,
    "历史遗址": 45,
    "古村镇": 90,
    "特色街区": 60,
    "创意园区": 45,

    # Shopping & food
    "购物中心": 45,
    "商业步行街": 60,
    "夜市": 45,
    "美食街": 45,
    "特色餐厅": 30,

    # Entertainment & nightlife
    "电影院": 120,
    "剧院": 90,
    "音乐厅": 90,
    "夜游": 45,
    "游船": 45,
    "观景台": 20,
    "缆车": 20,

    # Sports & outdoor
    "运动场馆": 60,
    "滑雪场": 150,
    "高尔夫球场": 90,
    "登山": 120,
    "徒步路线": 120,

    # Fallback
    "default": 60,
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
        # Try exact match first, then pick the longest matching key
        # (most specific). Amap multi-level strings like
        # "风景名胜;风景名胜;寺庙道观" should match "寺庙道观" (60 min)
        # not just "风景名胜" (120 min).
        if category in CATEGORY_DURATION_MAP:
            base = CATEGORY_DURATION_MAP[category]
        else:
            best_key = ""
            for key, dur in CATEGORY_DURATION_MAP.items():
                if key in category and len(key) > len(best_key):
                    best_key = key
                    base = dur

    multiplier = 1.0

    # Importance adjustment (5A/4A etc.)
    if importance:
        clean = importance.strip().upper()
        for label, mult in IMPORTANCE_MULTIPLIER.items():
            if label in clean:
                multiplier = mult
                break

    # Rating boost: continuous scale for diversity
    # 4.0 → 1.0x, 4.5 → 1.08x, 5.0 → 1.16x
    if rating is not None and rating >= 4.0:
        multiplier *= 1.0 + (rating - 4.0) * 0.16

    # Popularity boost: continuous scale, capped at +10%
    if review_count is not None and review_count > 0:
        multiplier *= 1.0 + min(review_count / 10000, 0.1)

    # Cap at reasonable bounds
    estimated = int(base * multiplier)
    return min(max(estimated, 15), 360)


def estimate_daily_capacity(
    poi_durations: list[int],
    avg_commute_min: int = 15,
    meal_break_min: int = 75,
    max_day_min: int = 810,  # 13.5h active time (8:30–22:00)
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

    return max(count, 3)  # at least 3 POIs per day


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
