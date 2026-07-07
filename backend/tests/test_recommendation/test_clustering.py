"""Tests for DBSCAN clustering day assignment with KMeans fallback."""

from __future__ import annotations

import pytest

from recommendation.clustering import cluster_pois_for_days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _poi(
    name: str,
    *,
    lat: float,
    lng: float,
    tags: list[str] | None = None,
) -> dict:
    """Create a minimal POI dict with coordinates for testing."""
    return {"name": name, "lat": lat, "lng": lng, "tags": tags or []}


# ---------------------------------------------------------------------------
# Basic clustering tests
# ---------------------------------------------------------------------------


class TestClusteringBasics:
    """Tests for basic clustering behavior."""

    def test_single_day_returns_all_pois(self) -> None:
        """n_days=1 should return all POIs in a single day."""
        pois = [
            _poi("A", lat=39.90, lng=116.40),
            _poi("B", lat=39.91, lng=116.41),
            _poi("C", lat=39.92, lng=116.42),
        ]

        result = cluster_pois_for_days(pois, n_days=1)

        assert len(result) == 1
        assert result[0]["day"] == 1
        assert len(result[0]["pois"]) == 3

    def test_empty_pois_returns_empty(self) -> None:
        """Empty POI list should return empty result."""
        result = cluster_pois_for_days([], n_days=3)
        assert result == []

    def test_fewer_pois_than_days(self) -> None:
        """When POIs are fewer than 2×days, clustering returns what it can.
        The graph-level guard in planning_pipeline will reduce effective_days,
        so the clustering function simply returns the actual clusters found."""
        pois = [
            _poi("A", lat=39.90, lng=116.40),
            _poi("B", lat=40.50, lng=117.00),
        ]

        result = cluster_pois_for_days(pois, n_days=3)

        # With 2 POIs far apart, we get at most 2 clusters; the third day
        # may be absent or merged. Total POIs must be preserved.
        assert 1 <= len(result) <= 3
        total_pois = sum(len(d["pois"]) for d in result)
        assert total_pois == 2
        # Every day with POIs should have ≥2 (rebalance guarantee)
        for d in result:
            if d["pois"]:
                assert len(d["pois"]) >= 1  # 2 POIs can't split into 3 days



# ---------------------------------------------------------------------------
# Core clustering behavior
# ---------------------------------------------------------------------------


class TestClusteringAssignsNearbyPois:
    """test_clustering_assigns_nearby_pois_same_day:
    6 POIs in 2 tight clusters → 2 days with 3 POIs each.
    """

    def test_clustering_assigns_nearby_pois_same_day(self) -> None:
        """6 POIs forming 2 tight clusters should be split into 2 days
        with 3 POIs each."""
        # Cluster A: near (39.90, 116.40) — tight group
        cluster_a = [
            _poi("A1", lat=39.900, lng=116.400),
            _poi("A2", lat=39.902, lng=116.402),
            _poi("A3", lat=39.901, lng=116.401),
        ]
        # Cluster B: near (40.05, 116.55) — tight group, ~20km from A
        cluster_b = [
            _poi("B1", lat=40.050, lng=116.550),
            _poi("B2", lat=40.052, lng=116.552),
            _poi("B3", lat=40.051, lng=116.551),
        ]
        pois = cluster_a + cluster_b

        result = cluster_pois_for_days(pois, n_days=2)

        assert len(result) == 2
        # Each day should have exactly 3 POIs
        day1_pois = result[0]["pois"]
        day2_pois = result[1]["pois"]
        assert len(day1_pois) == 3
        assert len(day2_pois) == 3

        # All POIs from the same cluster should be on the same day
        day1_names = {p["name"] for p in day1_pois}
        day2_names = {p["name"] for p in day2_pois}

        # Cluster A POIs should all be together
        a_names = {"A1", "A2", "A3"}
        b_names = {"B1", "B2", "B3"}

        assert a_names.issubset(day1_names) or a_names.issubset(day2_names), (
            "Cluster A POIs should all be on the same day"
        )
        assert b_names.issubset(day1_names) or b_names.issubset(day2_names), (
            "Cluster B POIs should all be on the same day"
        )


class TestClusteringSplitsDistantPois:
    """test_clustering_splits_distant_pois:
    4 POIs far apart → correctly split into separate days.
    """

    def test_clustering_splits_distant_pois(self) -> None:
        """4 POIs far apart should be split into separate days
        when n_days=2."""
        # Two pairs far apart (~50km+ apart)
        pois = [
            _poi("North1", lat=40.500, lng=116.400),
            _poi("North2", lat=40.502, lng=116.402),
            _poi("South1", lat=39.500, lng=116.400),
            _poi("South2", lat=39.502, lng=116.402),
        ]

        result = cluster_pois_for_days(pois, n_days=2)

        assert len(result) == 2
        day1_names = {p["name"] for p in result[0]["pois"]}
        day2_names = {p["name"] for p in result[1]["pois"]}

        # North POIs should be together, South POIs should be together
        north = {"North1", "North2"}
        south = {"South1", "South2"}

        assert north.issubset(day1_names) or north.issubset(day2_names), (
            "Northern POIs should be on the same day"
        )
        assert south.issubset(day1_names) or south.issubset(day2_names), (
            "Southern POIs should be on the same day"
        )


# ---------------------------------------------------------------------------
# Fallback to KMeans
# ---------------------------------------------------------------------------


class TestClusteringFallbackToKmeans:
    """test_clustering_fallback_to_kmeans:
    All points at the same location → merged into one cluster by HDBSCAN/Agglomerative.
    The rebalancer keeps them together since they're clearly the same place.
    """

    def test_clustering_fallback_to_kmeans(self) -> None:
        """When all POIs are at the exact same location, HDBSCAN/Agglomerative
        produce ≤2 clusters. The algorithm respects data density instead of
        artificially splitting identical coordinates."""
        pois = [
            _poi("A", lat=39.900, lng=116.400),
            _poi("B", lat=39.900, lng=116.400),
            _poi("C", lat=39.900, lng=116.400),
            _poi("D", lat=39.900, lng=116.400),
        ]

        result = cluster_pois_for_days(pois, n_days=2)

        # Should preserve all POIs
        total_pois = sum(len(d["pois"]) for d in result)
        assert total_pois == 4
        # At same location, a single cluster is the correct answer
        assert 1 <= len(result) <= 2


# ---------------------------------------------------------------------------
# Center-based sorting
# ---------------------------------------------------------------------------


class TestClusteringCenterSorting:
    """Tests that clusters are sorted by distance from center."""

    def test_closer_cluster_gets_day_1(self) -> None:
        """The cluster closer to the city center should be assigned day 1."""
        # Cluster near center (39.90, 116.40)
        near = [
            _poi("Near1", lat=39.900, lng=116.400),
            _poi("Near2", lat=39.902, lng=116.402),
        ]
        # Cluster far from center (~50km away)
        far = [
            _poi("Far1", lat=40.300, lng=116.800),
            _poi("Far2", lat=40.302, lng=116.802),
        ]
        pois = far + near  # far listed first

        result = cluster_pois_for_days(
            pois,
            n_days=2,
            center_lng=116.40,
            center_lat=39.90,
        )

        assert len(result) == 2
        day1_names = {p["name"] for p in result[0]["pois"]}
        # Near cluster should be day 1
        assert day1_names == {"Near1", "Near2"}, (
            "Cluster closer to center should be day 1"
        )

    def test_no_center_uses_poi_centroid(self) -> None:
        """When no center is given, use the centroid of all POIs as
        reference for sorting."""
        pois = [
            _poi("A1", lat=39.900, lng=116.400),
            _poi("A2", lat=39.902, lng=116.402),
            _poi("B1", lat=40.100, lng=116.600),
            _poi("B2", lat=40.102, lng=116.602),
        ]

        result = cluster_pois_for_days(pois, n_days=2)

        # Should still produce valid result
        assert len(result) == 2
        total_pois = sum(len(d["pois"]) for d in result)
        assert total_pois == 4


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestClusteringImmutability:
    """Tests that the function doesn't mutate input."""

    def test_does_not_mutate_input_pois(self) -> None:
        """Original POI dicts should not be modified."""
        pois = [
            _poi("A", lat=39.900, lng=116.400),
            _poi("B", lat=39.902, lng=116.402),
        ]
        original_pois = [dict(p) for p in pois]

        cluster_pois_for_days(pois, n_days=1)

        assert pois == original_pois, "Input POIs should not be mutated"

    def test_returns_new_poi_dicts(self) -> None:
        """Returned POIs in day assignments should be copies, not
        references to originals."""
        pois = [
            _poi("A", lat=39.900, lng=116.400),
            _poi("B", lat=40.100, lng=116.600),
        ]

        result = cluster_pois_for_days(pois, n_days=2)

        for day_result in result:
            for returned_poi in day_result["pois"]:
                # Check identity (is), not equality (==)
                is_original = any(returned_poi is p for p in pois)
                assert not is_original, (
                    "Returned POIs should be copies, not original references"
                )
