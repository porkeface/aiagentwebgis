"""Tests for duration_estimator — POI visit duration and daily capacity estimation."""

import pytest
from app.services.duration_estimator import (
    estimate_visit_duration,
    estimate_daily_capacity,
    estimate_poi_duration_from_dict,
    CATEGORY_DURATION_MAP,
    IMPORTANCE_MULTIPLIER,
)

# New defaults as of 2026-07: max_day_min=810, avg_commute=15, meal_break=75
# Base durations lowered (e.g. 风景名胜 180→120, default 90→60)


class TestEstimateVisitDuration:
    """Unit tests for estimate_visit_duration."""

    def test_known_category_exact_match(self):
        d = estimate_visit_duration(category="博物馆")
        assert d == 120

    def test_known_category_substring_match(self):
        d = estimate_visit_duration(category="博物馆;文化宫")
        assert d == 120

    def test_fallback_to_default(self):
        d = estimate_visit_duration(category="未知分类XYZ")
        assert d == 60  # new default

    def test_none_category_uses_default(self):
        d = estimate_visit_duration(category=None)
        assert d == 60  # new default

    def test_importance_5a_boosts(self):
        base = estimate_visit_duration(category="博物馆")  # 120
        boosted = estimate_visit_duration(category="博物馆", importance="5A")
        assert boosted == int(120 * 1.3)  # 156

    def test_importance_4a_boosts(self):
        # 公园 base is now 60 (was 90)
        d = estimate_visit_duration(category="公园", importance="4A")
        assert d == int(60 * 1.15)  # 69

    def test_importance_3a_no_change(self):
        # 寺庙道观 base is now 60 (was 90)
        d = estimate_visit_duration(category="寺庙道观", importance="3A")
        assert d == 60

    def test_importance_2a_reduces(self):
        # 风景名胜 base is now 120 (was 180)
        d = estimate_visit_duration(category="风景名胜", importance="2A")
        assert d == int(120 * 0.85)  # 102

    def test_high_rating_boost(self):
        # rating=4.5 → multiplier = 1.0 + 0.5*0.16 = 1.08
        base = estimate_visit_duration(category="博物馆", rating=4.5)
        assert base == int(120 * 1.08)  # 129

    def test_low_rating_no_boost(self):
        d = estimate_visit_duration(category="博物馆", rating=4.0)
        assert d == 120

    def test_high_review_count_boost(self):
        # review_count=2000 → multiplier = 1.0 + min(2000/10000, 0.1) = 1.1
        base = estimate_visit_duration(category="博物馆", review_count=2000)
        assert base == int(120 * 1.1)  # 132

    def test_low_review_count_no_boost(self):
        # review_count=500 → 1.0 + 500/10000 = 1.05
        d = estimate_visit_duration(category="博物馆", review_count=500)
        assert d == int(120 * 1.05)  # 126

    def test_combined_boosts(self):
        # 博物馆=120, 5A=1.3, rating=4.6→1.096, review_count=2000→1.1 (=1+min(2000/10000,0.1))
        d = estimate_visit_duration(
            category="博物馆", importance="5A", rating=4.6, review_count=2000
        )
        assert d == int(120 * 1.3 * 1.096 * 1.1)  # 188

    def test_clamps_minimum(self):
        d = estimate_visit_duration(category="火车站", importance="A")
        # 火车站=15, A=0.7 → 10.5 → clamped to 15
        assert d == 15

    def test_clamps_maximum(self):
        # 游乐园=180, 5A=1.3, rating=4.8→1.128, review=5000→1.1
        d = estimate_visit_duration(
            category="游乐园", importance="5A", rating=4.8, review_count=5000
        )
        # 180 * 1.3 * 1.128 * 1.1 = 290 (under 360, no clamp)
        assert d == 290

    def test_empty_string_category(self):
        d = estimate_visit_duration(category="")
        assert d == 60  # new default

    def test_importance_case_insensitive(self):
        d1 = estimate_visit_duration(category="博物馆", importance="5a")
        d2 = estimate_visit_duration(category="博物馆", importance="5A")
        assert d1 == d2


class TestEstimateDailyCapacity:
    """Unit tests for estimate_daily_capacity.

    New defaults: max_day_min=810, avg_commute=15, meal_break=75.
    Available = 810 - 75 = 735 minutes.
    """

    def test_four_short_pois_fit(self):
        # 4×60 = 240 visit, + 3×15 commute = 285, total 525 < 735
        cap = estimate_daily_capacity([60, 60, 60, 60])
        assert cap == 4

    def test_long_pois_limit_count(self):
        # 240, then +240+15=255, then +240+15=255 → total 240+255+255=750 > 735 → 2
        # But floor is now 3 — ensure we get at least 3
        cap = estimate_daily_capacity([240, 240, 240])
        assert cap == 3

    def test_minimum_three_pois(self):
        # Even if durations are huge, return at least 3
        cap = estimate_daily_capacity([400, 400, 400])
        assert cap == 3

    def test_mixed_durations(self):
        # 180 + (120+15) + (90+15) + (60+15) + (45+15) + (30+15)
        # = 180 + 135 + 105 + 75 + 60 + 45 = 600 < 735 → all 6 fit
        cap = estimate_daily_capacity([180, 120, 90, 60, 45, 30])
        assert cap == 6

    def test_empty_list_returns_minimum(self):
        cap = estimate_daily_capacity([])
        assert cap == 3

    def test_custom_commute(self):
        # 120 + (120+30)×4 = 120 + 150×4 = 720 < 735 → all 5 fit
        cap = estimate_daily_capacity([120, 120, 120, 120, 120], avg_commute_min=30)
        assert cap == 5


class TestEstimatePoiDurationFromDict:
    """Tests for the POI dict convenience wrapper."""

    def test_basic_poi(self):
        poi = {"category": "博物馆", "rating": 4.5, "review_count": 500}
        d = estimate_poi_duration_from_dict(poi)
        # rating=4.5 → 1.08x, reviews=500 → 1.05x
        assert d == int(120 * 1.08 * 1.05)  # 136

    def test_amap_poi_with_type_field(self):
        # 风景名胜 base is now 120 (was 180)
        poi = {"type": "风景名胜;国家级景点", "importance": "5A"}
        d = estimate_poi_duration_from_dict(poi)
        assert d == int(120 * 1.3)  # 156

    def test_poi_with_all_fields_missing(self):
        poi = {}
        d = estimate_poi_duration_from_dict(poi)
        assert d == 60  # new default

    def test_poi_with_opentime_cost_tags(self):
        # 公园 base is now 60 (was 90)
        # rating=4.2 → 1.032, 4A=1.15
        poi = {
            "category": "公园",
            "rating": 4.2,
            "importance": "4A",
            "opentime": "06:00-22:00",
            "cost": "免费",
            "tags": ["赏花", "亲子"],
            "business_area": "朝阳区",
        }
        d = estimate_poi_duration_from_dict(poi)
        assert d == int(60 * 1.15 * 1.032)  # 71


class TestCategoryDurationMap:
    """Sanity checks on the category map."""

    def test_all_values_in_range(self):
        for cat, mins in CATEGORY_DURATION_MAP.items():
            if cat == "default":
                continue
            assert 10 <= mins <= 360, f"{cat} duration {mins} out of range"

    def test_importance_multipliers_in_range(self):
        for level, mult in IMPORTANCE_MULTIPLIER.items():
            assert 0.5 <= mult <= 2.0, f"{level} multiplier {mult} out of range"
