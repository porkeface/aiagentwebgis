"""Tests for recommendation pipeline orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# Test fixtures - mock POI data
MOCK_POIS = [
    {
        "id": "poi_1",
        "name": "Temple 1",
        "city": "Beijing",
        "lat": 39.9042,
        "lng": 116.4074,
        "tags": ["culture", "history"],
        "rating": 4.5,
        "review_count": 100,
    },
    {
        "id": "poi_2",
        "name": "Park 1",
        "city": "Beijing",
        "lat": 39.9142,
        "lng": 116.4174,
        "tags": ["nature", "park"],
        "rating": 4.2,
        "review_count": 80,
    },
    {
        "id": "poi_3",
        "name": "Museum 1",
        "city": "Beijing",
        "lat": 39.9242,
        "lng": 116.4274,
        "tags": ["culture", "museum"],
        "rating": 4.8,
        "review_count": 150,
    },
    {
        "id": "poi_4",
        "name": "Restaurant 1",
        "city": "Beijing",
        "lat": 39.9342,
        "lng": 116.4374,
        "tags": ["food", "restaurant"],
        "rating": 4.0,
        "review_count": 60,
    },
    {
        "id": "poi_5",
        "name": "Shopping 1",
        "city": "Beijing",
        "lat": 39.9442,
        "lng": 116.4474,
        "tags": ["shopping", "mall"],
        "rating": 3.8,
        "review_count": 40,
    },
    {
        "id": "poi_6",
        "name": "Temple 2",
        "city": "Beijing",
        "lat": 39.9542,
        "lng": 116.4574,
        "tags": ["culture", "history"],
        "rating": 4.3,
        "review_count": 90,
    },
]


# ---------------------------------------------------------------------------
# test_full_pipeline_produces_daily_plans
# ---------------------------------------------------------------------------


class TestFullPipelineProducesDailyPlans:
    """Verify pipeline produces valid daily_plans structure."""

    async def test_full_pipeline_produces_daily_plans(self) -> None:
        """Test that pipeline produces valid daily_plans structure."""
        from recommendation.pipeline import run_recommendation_pipeline

        mock_spatial_filter = AsyncMock(return_value=(MOCK_POIS, False))

        with patch(
            "recommendation.pipeline.spatial_filter_pois",
            mock_spatial_filter,
        ):
            result = await run_recommendation_pipeline(
                city="Beijing",
                preferences=["culture", "history"],
                days=2,
                weights={
                    "preference": 0.3,
                    "distance": 0.2,
                    "rating": 0.2,
                    "time": 0.1,
                    "popularity": 0.2,
                },
                center_lng=116.4074,
                center_lat=39.9042,
                lambda_mmr=0.7,
                mmr_k=5,
            )

        # Verify top-level structure
        assert "candidate_count" in result
        assert "scored_count" in result
        assert "diverse_count" in result
        assert "daily_plans" in result

        # Verify daily_plans is a list
        assert isinstance(result["daily_plans"], list)
        assert len(result["daily_plans"]) > 0

        # Verify each day has required fields
        for day_plan in result["daily_plans"]:
            assert "day" in day_plan
            assert "pois" in day_plan
            assert "total_distance_km" in day_plan
            assert "segments" in day_plan

            # Verify POIs have scores
            for poi in day_plan["pois"]:
                assert "score" in poi

            # Verify segments structure
            assert isinstance(day_plan["segments"], list)
            for segment in day_plan["segments"]:
                assert "from_poi_id" in segment
                assert "to_poi_id" in segment
                assert "distance_km" in segment


# ---------------------------------------------------------------------------
# test_pipeline_returns_correct_number_of_days
# ---------------------------------------------------------------------------


class TestPipelineReturnsCorrectNumberOfDays:
    """Verify pipeline produces the requested number of days."""

    async def test_pipeline_returns_correct_number_of_days(self) -> None:
        """Test that pipeline produces the requested number of days."""
        from recommendation.pipeline import run_recommendation_pipeline

        days = 3
        mock_spatial_filter = AsyncMock(return_value=(MOCK_POIS, False))

        with patch(
            "recommendation.pipeline.spatial_filter_pois",
            mock_spatial_filter,
        ):
            result = await run_recommendation_pipeline(
                city="Beijing",
                preferences=["culture"],
                days=days,
                weights={
                    "preference": 0.4,
                    "distance": 0.3,
                    "rating": 0.3,
                    "time": 0.0,
                    "popularity": 0.0,
                },
                center_lng=116.4074,
                center_lat=39.9042,
            )

        assert len(result["daily_plans"]) == days

        # Verify day numbers are sequential starting from 1
        for idx, day_plan in enumerate(result["daily_plans"], start=1):
            assert day_plan["day"] == idx


# ---------------------------------------------------------------------------
# Additional tests
# ---------------------------------------------------------------------------


class TestPipelineEdgeCases:
    """Test pipeline edge cases."""

    async def test_pipeline_with_single_day(self) -> None:
        """Test pipeline with days=1."""
        from recommendation.pipeline import run_recommendation_pipeline

        mock_spatial_filter = AsyncMock(return_value=(MOCK_POIS, False))

        with patch(
            "recommendation.pipeline.spatial_filter_pois",
            mock_spatial_filter,
        ):
            result = await run_recommendation_pipeline(
                city="Beijing",
                preferences=["nature"],
                days=1,
                weights={"preference": 0.5, "rating": 0.5},
                center_lng=116.4074,
                center_lat=39.9042,
            )

        assert len(result["daily_plans"]) == 1
        assert result["daily_plans"][0]["day"] == 1

    async def test_pipeline_counts_are_correct(self) -> None:
        """Test that pipeline returns correct counts at each stage."""
        from recommendation.pipeline import run_recommendation_pipeline

        mock_spatial_filter = AsyncMock(return_value=(MOCK_POIS, False))

        with patch(
            "recommendation.pipeline.spatial_filter_pois",
            mock_spatial_filter,
        ):
            result = await run_recommendation_pipeline(
                city="Beijing",
                preferences=["culture"],
                days=2,
                weights={"preference": 0.5, "rating": 0.5},
                center_lng=116.4074,
                center_lat=39.9042,
                mmr_k=4,
            )

        # candidate_count should match mock POIs
        assert result["candidate_count"] == len(MOCK_POIS)

        # scored_count should equal candidate_count (scoring doesn't filter)
        assert result["scored_count"] == result["candidate_count"]

        # diverse_count should be <= mmr_k
        assert result["diverse_count"] <= 4
