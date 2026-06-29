"""Tests for TSP route optimization."""

from __future__ import annotations

import pytest

from recommendation.tsp import haversine_km, optimize_daily_route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route_distance(pois: list[dict]) -> float:
    """Total haversine distance along a sequence of POIs."""
    total = 0.0
    for i in range(len(pois) - 1):
        total += haversine_km(
            pois[i]["lat"],
            pois[i]["lng"],
            pois[i + 1]["lat"],
            pois[i + 1]["lng"],
        )
    return total


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case handling for optimize_daily_route."""

    def test_empty_pois(self) -> None:
        result = optimize_daily_route([])
        assert result["ordered_pois"] == []
        assert result["total_distance_km"] == 0.0
        assert result["segments"] == []

    def test_single_poi_returns_same(self) -> None:
        poi = {"id": "only", "lng": 116.4, "lat": 39.9, "name": "Solo"}
        result = optimize_daily_route([poi])
        assert len(result["ordered_pois"]) == 1
        assert result["ordered_pois"][0]["id"] == "only"
        assert result["total_distance_km"] == 0.0
        assert result["segments"] == []

    def test_two_pois(self) -> None:
        pois = [
            {"id": "a", "lng": 116.0, "lat": 40.0},
            {"id": "b", "lng": 117.0, "lat": 40.0},
        ]
        result = optimize_daily_route(pois)
        assert len(result["ordered_pois"]) == 2
        assert len(result["segments"]) == 1
        assert result["total_distance_km"] > 0
        seg = result["segments"][0]
        ids = {seg["from_poi_id"], seg["to_poi_id"]}
        assert ids == {"a", "b"}


# ---------------------------------------------------------------------------
# Core optimization
# ---------------------------------------------------------------------------


class TestOptimization:
    """Core TSP optimization behaviour."""

    def test_tsp_reduces_total_distance_vs_input_order(self) -> None:
        """Zigzag input order should be improvable by TSP."""
        # 6 POIs: top-row left-to-right, then bottom-row right-to-left.
        # This creates a U-shape. NN from center (lower-left) + 2-opt
        # should find the much shorter left-column-then-right-column route.
        pois = [
            {"id": "a", "lng": 116.0, "lat": 40.1},  # top-left
            {"id": "b", "lng": 116.2, "lat": 40.1},  # top-mid
            {"id": "c", "lng": 116.4, "lat": 40.1},  # top-right
            {"id": "d", "lng": 116.4, "lat": 40.0},  # bottom-right
            {"id": "e", "lng": 116.2, "lat": 40.0},  # bottom-mid
            {"id": "f", "lng": 116.0, "lat": 40.0},  # bottom-left
        ]

        input_dist = _route_distance(pois)
        result = optimize_daily_route(pois, center_lng=116.0, center_lat=40.0)
        tsp_dist = result["total_distance_km"]

        # TSP should produce a strictly shorter route than the bad zigzag
        assert tsp_dist < input_dist
        # Improvement should be substantial (> 10 %)
        assert tsp_dist < input_dist * 0.9

    def test_tsp_preserves_all_pois(self) -> None:
        """All input POIs must appear in the output, unmodified."""
        pois = [
            {"id": f"p{i}", "lng": 116.0 + i * 0.05, "lat": 39.9 + i * 0.02, "name": f"Place {i}"}
            for i in range(8)
        ]

        result = optimize_daily_route(pois)
        ordered = result["ordered_pois"]

        assert len(ordered) == len(pois)

        # Same set of IDs
        in_ids = {p["id"] for p in pois}
        out_ids = {p["id"] for p in ordered}
        assert in_ids == out_ids

        # Extra fields carried through
        id_name = {p["id"]: p["name"] for p in pois}
        for p in ordered:
            assert p["name"] == id_name[p["id"]]

    def test_tsp_output_has_day_order(self) -> None:
        """Each output POI should carry a 1-based day_order field."""
        pois = [
            {"id": "x", "lng": 116.0, "lat": 40.0},
            {"id": "y", "lng": 116.1, "lat": 40.0},
            {"id": "z", "lng": 116.2, "lat": 40.0},
        ]
        result = optimize_daily_route(pois)
        orders = [p["day_order"] for p in result["ordered_pois"]]
        assert orders == [1, 2, 3]


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Validate the shape and consistency of the return dict."""

    def test_segment_count(self) -> None:
        n = 5
        pois = [
            {"id": f"s{i}", "lng": 116.0 + i * 0.1, "lat": 40.0}
            for i in range(n)
        ]
        result = optimize_daily_route(pois)
        assert len(result["segments"]) == n - 1

    def test_segment_poi_ids_chain(self) -> None:
        """segments[i].to == segments[i+1].from (contiguous chain)."""
        pois = [
            {"id": f"c{i}", "lng": 116.0 + i * 0.05, "lat": 39.9 + i * 0.03}
            for i in range(6)
        ]
        result = optimize_daily_route(pois)
        segs = result["segments"]
        for i in range(len(segs) - 1):
            assert segs[i]["to_poi_id"] == segs[i + 1]["from_poi_id"]

    def test_segment_ids_match_ordered_pois(self) -> None:
        """First/last segment IDs must match first/last POI."""
        pois = [
            {"id": f"m{i}", "lng": 116.0 + i * 0.1, "lat": 40.0}
            for i in range(4)
        ]
        result = optimize_daily_route(pois)
        ordered_ids = [p["id"] for p in result["ordered_pois"]]
        segs = result["segments"]

        assert segs[0]["from_poi_id"] == ordered_ids[0]
        assert segs[-1]["to_poi_id"] == ordered_ids[-1]

    def test_total_distance_matches_haversine_sum(self) -> None:
        """total_distance_km == sum of segment distances."""
        pois = [
            {"id": f"t{i}", "lng": 116.0 + i * 0.08, "lat": 39.95 + i * 0.04}
            for i in range(5)
        ]
        result = optimize_daily_route(pois)

        seg_sum = sum(s["distance_km"] for s in result["segments"])
        assert abs(result["total_distance_km"] - seg_sum) < 1e-9


# ---------------------------------------------------------------------------
# Determinism & starting point
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Reproducibility and center-based starting point."""

    def test_deterministic(self) -> None:
        pois = [
            {"id": f"d{i}", "lng": 116.0 + i * 0.1, "lat": 40.0 - i * 0.05}
            for i in range(7)
        ]
        r1 = optimize_daily_route(pois)
        r2 = optimize_daily_route(pois)
        assert [p["id"] for p in r1["ordered_pois"]] == [p["id"] for p in r2["ordered_pois"]]
        assert r1["total_distance_km"] == r2["total_distance_km"]

    def test_uses_provided_center_as_start(self) -> None:
        """Center near one end should produce a shorter route than far end."""
        # 6 POIs in 2 rows × 3 cols
        pois = [
            {"id": "a", "lng": 116.0, "lat": 40.1},  # top-left
            {"id": "b", "lng": 116.2, "lat": 40.1},  # top-mid
            {"id": "c", "lng": 116.4, "lat": 40.1},  # top-right
            {"id": "d", "lng": 116.4, "lat": 40.0},  # bottom-right
            {"id": "e", "lng": 116.2, "lat": 40.0},  # bottom-mid
            {"id": "f", "lng": 116.0, "lat": 40.0},  # bottom-left
        ]

        # Center near bottom-left → NN starts at poi_f → optimal sweep
        r_near = optimize_daily_route(pois, center_lng=116.0, center_lat=40.0)
        # Center near top-right → NN starts at poi_c → sub-optimal sweep
        r_far = optimize_daily_route(pois, center_lng=116.4, center_lat=40.1)

        assert r_near["total_distance_km"] <= r_far["total_distance_km"]

    def test_poi_without_id(self) -> None:
        """POIs lacking an 'id' field should still work."""
        pois = [
            {"lng": 116.0, "lat": 40.0},
            {"lng": 116.1, "lat": 40.0},
            {"lng": 116.2, "lat": 40.0},
        ]
        result = optimize_daily_route(pois)
        assert len(result["ordered_pois"]) == 3
        assert len(result["segments"]) == 2
        assert result["total_distance_km"] > 0

    def test_does_not_mutate_input(self) -> None:
        """Input POI dicts must not be modified."""
        pois = [
            {"id": "orig", "lng": 116.0, "lat": 40.0, "name": "Test"},
        ]
        import copy

        original = copy.deepcopy(pois)
        optimize_daily_route(pois)
        assert pois == original
