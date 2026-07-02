"""Tests for duration_estimator — POI visit duration and daily capacity estimation."""

import pytest
from app.services.duration_estimator import (
    estimate_visit_duration,
    estimate_daily_capacity,
    estimate_poi_duration_from_dict,
    CATEGORY_DURATION_MAP,
    IMPORTANCE_MULTIPLIER,
)


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
        assert d == 90

    def test_none_category_uses_default(self):
        d = estimate_visit_duration(category=None)
        assert d == 90

    def test_importance_5a_boosts(self):
        base = estimate_visit_duration(category="博物馆")  # 120
        boosted = estimate_visit_duration(category="博物馆", importance="5A")
        assert boosted == int(120 * 1.3)  # 156

    def test_importance_4a_boosts(self):
        d = estimate_visit_duration(category="公园", importance="4A")
        assert d == int(90 * 1.15)

    def test_importance_3a_no_change(self):
        d = estimate_visit_duration(category="寺庙道观", importance="3A")
        assert d == 90

    def test_importance_2a_reduces(self):
        d = estimate_visit_duration(category="风景名胜", importance="2A")
        assert d == int(180 * 0.85)

    def test_high_rating_boost(self):
        base = estimate_visit_duration(category="博物馆", rating=4.5)
        assert base == int(120 * 1.1)  # 132

    def test_low_rating_no_boost(self):
        d = estimate_visit_duration(category="博物馆", rating=4.0)
        assert d == 120

    def test_high_review_count_boost(self):
        base = estimate_visit_duration(category="博物馆", review_count=2000)
        assert base == int(120 * 1.1)

    def test_low_review_count_no_boost(self):
        d = estimate_visit_duration(category="博物馆", review_count=500)
        assert d == 120

    def test_combined_boosts(self):
        # 博物馆=120, 5A=1.3, rating>=4.5=1.1, review_count>1000=1.1
        d = estimate_visit_duration(
            category="博物馆", importance="5A", rating=4.6, review_count=2000
        )
        assert d == int(120 * 1.3 * 1.1 * 1.1)

    def test_clamps_minimum(self):
        d = estimate_visit_duration(category="火车站", importance="A")
        # 火车站=15, A=0.7 → 10.5 → clamped to 15
        assert d == 15

    def test_clamps_maximum(self):
        # 游乐园=240, 5A=1.3, rating=4.5=1.1, review=2000=1.1 → ~377 → clamped to 360
        d = estimate_visit_duration(
            category="游乐园", importance="5A", rating=4.8, review_count=5000
        )
        assert d == 360

    def test_empty_string_category(self):
        d = estimate_visit_duration(category="")
        assert d == 90

    def test_importance_case_insensitive(self):
        d1 = estimate_visit_duration(category="博物馆", importance="5a")
        d2 = estimate_visit_duration(category="博物馆", importance="5A")
        assert d1 == d2


class TestEstimateDailyCapacity:
    """Unit tests for estimate_daily_capacity."""

    def test_four_short_pois_fit(self):
        # 4×60 = 240 visit, + 3×20 commute = 300, fits in 600 (660-60 meal)
        cap = estimate_daily_capacity([60, 60, 60, 60])
        assert cap == 4

    def test_long_pois_limit_count(self):
        # 3×240=720 visit, first: 240 fits, second: 240+20=260 total 500 fits,
        # third: 240+20=260 total 760 > 600 → stops → 2
        cap = estimate_daily_capacity([240, 240, 240])
        assert cap == 2

    def test_minimum_two_pois(self):
        # Even if durations are huge, return at least 2
        cap = estimate_daily_capacity([400, 400, 400])
        assert cap == 2

    def test_mixed_durations(self):
        # 180 + (120+20) + (90+20) + (60+20) = 180+140+110+80 = 510 fits
        # Next: (45+20) = 65 → 575 fits
        # Next: (30+20) = 50 → 625 > 600 → stop at 5
        cap = estimate_daily_capacity([180, 120, 90, 60, 45, 30])
        assert cap == 5

    def test_empty_list_returns_two(self):
        cap = estimate_daily_capacity([])
        assert cap == 2

    def test_custom_commute(self):
        # 120 + (120+30) + (120+30) = 420 fits,
        # + (120+30) = 570 fits, + (120+30) = 720 > 600 → 4
        cap = estimate_daily_capacity([120, 120, 120, 120, 120], avg_commute_min=30)
        assert cap == 4


class TestEstimatePoiDurationFromDict:
    """Tests for the POI dict convenience wrapper."""

    def test_basic_poi(self):
        poi = {"category": "博物馆", "rating": 4.5, "review_count": 500}
        d = estimate_poi_duration_from_dict(poi)
        assert d == int(120 * 1.1)  # only rating boost

    def test_amap_poi_with_type_field(self):
        # Amap uses "type" instead of "category"
        poi = {"type": "风景名胜;国家级景点", "importance": "5A"}
        d = estimate_poi_duration_from_dict(poi)
        assert d == int(180 * 1.3)

    def test_poi_with_all_fields_missing(self):
        poi = {}
        d = estimate_poi_duration_from_dict(poi)
        assert d == 90  # default

    def test_poi_with_opentime_cost_tags(self):
        # Extra fields should not break the estimator
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
        assert d == int(90 * 1.15)


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
