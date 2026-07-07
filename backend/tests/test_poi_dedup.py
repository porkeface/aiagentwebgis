"""Unit tests for semantic + spatial POI dedup (deduplicate_pois).

Coverage:
- Rule 1: name containment ("西湖公园" vs "西湖公园-真趣")
- Rule 2: same coordinates (< 10 m)
- Rule 3: high name similarity + close
- Rule 4: same base-name ("武夷山景区" vs "武夷山景区-南门")
- Rule 5: sub-POI with rating difference (< 2 km)
- No false positive: different POIs far apart survive
- No false positive: different POIs with same base-name but > 150 m
- Edge cases: empty list, single POI, all duplicates
"""

import pytest
from agent.tools.poi_dedup import deduplicate_pois


# ── Helpers ──────────────────────────────────────────────────────────────

def _poi(name, lng, lat, id="0", rating=None, review_count=None):
    d = {"name": name, "lng": lng, "lat": lat, "id": id}
    if rating is not None:
        d["rating"] = rating
    if review_count is not None:
        d["review_count"] = review_count
    return d


# ── Rule 1: name containment ─────────────────────────────────────────────

def test_rule1_name_containment_substring():
    """'西湖公园' in '西湖公园-真趣' + same spot → dedup."""
    pois = [
        _poi("西湖公园", 120.15, 30.25, id="a", rating=4.0, review_count=500),
        _poi("西湖公园-真趣", 120.15, 30.25, id="b", rating=3.8, review_count=50),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"  # higher rating wins


def test_rule1_name_containment_higher_rating_wins():
    """The POI with higher rating survives name-containment dedup."""
    pois = [
        _poi("三坊七巷", 119.30, 26.08, id="a", rating=3.5),
        _poi("三坊七巷-售票处", 119.30, 26.08, id="b", rating=4.5),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "b"


def test_rule1_name_containment_far_apart_no_dedup():
    """Same name but > 500 m → NOT deduped (could be different instances)."""
    pois = [
        _poi("中山公园", 116.40, 39.90, id="a"),
        _poi("中山公园-北门", 116.45, 39.92, id="b"),  # ~5 km away
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 2


def test_rule1_name_containment_same_rating_review_count_tie():
    """Equal rating + review_count — stable tie-break by id."""
    pois = [
        _poi("西湖公园", 120.15, 30.25, id="a", rating=4.0, review_count=100),
        _poi("西湖公园-真趣", 120.15, 30.25, id="b", rating=4.0, review_count=100),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    # Lower id wins as tie-breaker
    assert result[0]["id"] == "a"


# ── Rule 2: same coordinates ─────────────────────────────────────────────

def test_rule2_same_coordinates():
    pois = [
        _poi("P1", 120.0, 30.0, id="a", rating=4.2),
        _poi("P2", 120.0, 30.0, id="b", rating=3.9),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_rule2_same_coordinates_different_names():
    """Even with different names, exact same coords → dedup."""
    pois = [
        _poi("星巴克（西湖店）", 120.15, 30.25, id="a", rating=4.0),
        _poi("Starbucks West Lake", 120.15, 30.25, id="b", rating=3.5),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1


# ── Rule 3: high similarity + close ─────────────────────────────────────

def test_rule3_high_similarity():
    pois = [
        _poi("鼓浪屿风景名胜区", 118.068, 24.448, id="a", rating=4.5, review_count=3000),
        _poi("鼓浪屿•风景名胜区", 118.069, 24.449, id="b", rating=3.9, review_count=200),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"


# ── Rule 4: same base-name ────────────────────────────────────────────────

def test_rule4_same_basename():
    pois = [
        _poi("武夷山景区", 117.99, 27.72, id="a", rating=4.6, review_count=5000),
        _poi("武夷山景区-南门", 117.992, 27.721, id="b", rating=3.7, review_count=100),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_rule4_same_basename_with_pipe():
    pois = [
        _poi("故宫博物院", 116.397, 39.916, id="a", rating=4.8),
        _poi("故宫博物院|午门入口", 116.398, 39.915, id="b", rating=4.0),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_rule4_same_basename_with_slash():
    pois = [
        _poi("黄山风景区", 118.17, 30.13, id="a", rating=4.5),
        _poi("黄山风景区/北大门", 118.171, 30.131, id="b", rating=4.0),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1


def test_rule4_same_basename_with_chinese_parens():
    pois = [
        _poi("颐和园", 116.27, 40.00, id="a", rating=4.7),
        _poi("颐和园（东宫门）", 116.271, 40.001, id="b", rating=4.2),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1


def test_rule4_same_basename_far_apart():
    """Same base name but > 150 m → NOT deduped."""
    pois = [
        _poi("夫子庙", 118.79, 32.02, id="a"),
        _poi("夫子庙-秦淮河画舫", 118.80, 32.03, id="b"),  # > 1 km
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 2


# ── Rule 5: sub-POI ──────────────────────────────────────────────────────

def test_rule5_sub_poi():
    """'故宫博物院' starts with '故宫' → keep the more specific one."""
    pois = [
        _poi("故宫", 116.397, 39.916, id="a", rating=4.0),
        _poi("故宫博物院", 116.398, 39.917, id="b", rating=4.2),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "b"  # more specific wins (rating close)


def test_rule5_sub_poi_rating_gap():
    """Sub-POI: keep specific unless generic is MUCH better rated."""
    pois = [
        _poi("灵隐寺", 120.10, 30.24, id="a", rating=4.9, review_count=8000),
        _poi("灵隐寺飞来峰景区", 120.101, 30.241, id="b", rating=3.2, review_count=100),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"  # rating gap >= 1.0, keep generic


def test_rule5_sub_poi_far_apart():
    """Sub-POI match but > 2 km → NOT deduped."""
    pois = [
        _poi("鼓山", 119.38, 26.07, id="a"),
        _poi("鼓山风景区", 119.42, 26.08, id="b"),  # ~4 km
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 2


# ── No false positive ────────────────────────────────────────────────────

def test_different_pois_survive():
    pois = [
        _poi("故宫", 116.397, 39.916, id="a"),
        _poi("颐和园", 116.272, 40.000, id="b"),
        _poi("天坛", 116.412, 39.883, id="c"),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 3
    assert {p["id"] for p in result} == {"a", "b", "c"}


def test_same_basename_different_places():
    """Same base name '中山公园' but different city suffixes → different places."""
    pois = [
        _poi("中山公园（武汉）", 114.30, 30.59, id="a"),
        _poi("中山公园（上海）", 121.47, 31.23, id="b"),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 2  # different cities, far apart


# ── Edge cases ────────────────────────────────────────────────────────────

def test_empty_list():
    assert deduplicate_pois([]) == []


def test_single_poi():
    pois = [_poi("西湖", 120.15, 30.25, id="a")]
    result = deduplicate_pois(pois)
    assert len(result) == 1


def test_missing_coordinates():
    pois = [
        _poi("P1", 120.0, 30.0, id="a"),
        _poi("P2", None, None, id="b"),  # no coords → skip rule evaluation
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 2  # can't determine distance, keep both


def test_all_duplicates():
    pois = [
        _poi("西湖公园", 120.15, 30.25, id="a", rating=4.5),
        _poi("西湖公园-真趣", 120.15, 30.25, id="b", rating=3.0),
        _poi("西湖公园-南门", 120.151, 30.251, id="c", rating=3.5),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_mixed_duplicates_and_unique():
    pois = [
        _poi("西湖公园", 120.15, 30.25, id="a", rating=4.5, review_count=500),  # dup
        _poi("西湖公园-真趣", 120.15, 30.25, id="b", rating=3.0, review_count=10),  # dup
        _poi("灵隐寺", 120.10, 30.24, id="c", rating=4.7),                         # unique
        _poi("雷峰塔", 120.145, 30.23, id="d", rating=4.3),                        # unique
        _poi("雷峰塔景区", 120.146, 30.231, id="e", rating=3.9),                   # dup of d
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 3
    ids = {p["id"] for p in result}
    assert ids == {"a", "c", "d"}


# ── Rule 6: service-facility suffix ────────────────────────────────────────

def test_service_facility_discarded():
    """售票处/停车场/卫生间 etc. should be discarded, keep the real POI."""
    pois = [
        _poi("崇圣寺三塔", 100.16, 25.70, id="a", rating=4.5),
        _poi("崇圣寺三塔售票处", 100.165, 25.705, id="b", rating=3.0),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"

def test_parking_lot_discarded():
    pois = [
        _poi("鼓浪屿", 118.065, 24.45, id="a", rating=4.6),
        _poi("鼓浪屿停车场", 118.07, 24.455, id="b", rating=3.5),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"

def test_toilet_discarded():
    pois = [
        _poi("中山公园", 121.47, 31.23, id="a", rating=4.3),
        _poi("中山公园公共厕所", 121.475, 31.235, id="b", rating=3.0),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1
    assert result[0]["id"] == "a"

def test_legit_expansion_not_mistaken_for_facility():
    """博物院/风景区 etc. are legitimate expansions, not facilities."""
    pois = [
        _poi("故宫", 116.397, 39.908, id="a", rating=4.7),
        _poi("故宫博物院", 116.402, 39.913, id="b", rating=4.8),
    ]
    result = deduplicate_pois(pois)
    assert len(result) == 1  # dedup via Rule 5 sub-POI, not facility rule
    # Should keep the higher-rated one
    assert result[0]["id"] == "b"
