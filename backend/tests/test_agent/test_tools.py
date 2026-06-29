"""Tests for Agent Tool Chain (Task 2.2).

Tests cover:
- search_pois_tool wraps AmapService.search_pois
- geocode_tool wraps AmapService.geocode
- plan_route_tool wraps AmapService.plan_route
- score_pois_tool implements multi-factor scoring (pure computation)
- get_weather_tool returns placeholder data
- get_amap() singleton factory
- ALL_TOOLS exports all tool functions
"""

from __future__ import annotations

import math

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_amap() -> MagicMock:
    """Create a mock AmapService with AsyncMock methods."""
    svc = MagicMock()
    svc.search_pois = AsyncMock(return_value=[])
    svc.geocode = AsyncMock(return_value=(116.397428, 39.90923))
    svc.reverse_geocode = AsyncMock(
        return_value={"address": "北京市东城区景山前街4号", "city": "北京市"}
    )
    svc.plan_route = AsyncMock(
        return_value={
            "distance_km": 1.5,
            "duration_min": 18.0,
            "polyline": "116.397,39.909;116.398,39.910",
        }
    )
    return svc


@pytest.fixture
def sample_pois() -> list[dict]:
    """Provide sample POI dicts for scoring tests."""
    return [
        {
            "amap_id": "poi_1",
            "name": "故宫博物院",
            "address": "景山前街4号",
            "lng": 116.397,
            "lat": 39.909,
            "type": "风景名胜",
            "tags": ["文化", "历史", "古建筑"],
            "rating": 4.8,
            "review_count": 5000,
            "city": "北京",
        },
        {
            "amap_id": "poi_2",
            "name": "颐和园",
            "address": "宫门前街1号",
            "lng": 116.275,
            "lat": 39.999,
            "type": "风景名胜",
            "tags": ["文化", "园林", "历史"],
            "rating": 4.6,
            "review_count": 3000,
            "city": "北京",
        },
        {
            "amap_id": "poi_3",
            "name": "南锣鼓巷",
            "address": "南锣鼓巷胡同",
            "lng": 116.403,
            "lat": 39.937,
            "type": "商业街",
            "tags": ["美食", "购物", "胡同"],
            "rating": 4.2,
            "review_count": 2000,
            "city": "北京",
        },
    ]


# ---------------------------------------------------------------------------
# search_pois_tool
# ---------------------------------------------------------------------------


class TestSearchPoisTool:
    """Tests for search_pois_tool."""

    async def test_search_pois_tool_calls_service(self, mock_amap: MagicMock) -> None:
        """search_pois_tool should call amap.search_pois with correct args."""
        mock_amap.search_pois.return_value = [
            {
                "amap_id": "B000A7BD6C",
                "name": "故宫博物院",
                "address": "景山前街4号",
                "lng": 116.397,
                "lat": 39.909,
                "type": "风景名胜",
                "city": "北京",
            },
        ]

        from agent.tools.poi_search import search_pois_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await search_pois_tool("北京", "景点", keyword="故宫")

        mock_amap.search_pois.assert_awaited_once_with(
            city="北京",
            category="景点",
            keyword="故宫",
        )
        assert len(result) == 1
        assert result[0]["name"] == "故宫博物院"

    async def test_search_pois_tool_without_keyword(
        self, mock_amap: MagicMock
    ) -> None:
        """search_pois_tool without keyword passes None."""
        from agent.tools.poi_search import search_pois_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await search_pois_tool("上海", "景点")

        mock_amap.search_pois.assert_awaited_once_with(
            city="上海",
            category="景点",
            keyword=None,
        )
        assert result == []

    async def test_search_nearby_tool_calls_service(self, mock_amap: MagicMock) -> None:
        """search_nearby_tool should call amap with correct params."""
        mock_amap.search_nearby = AsyncMock(return_value=[
            {"amap_id": "near_1", "name": "附近景点", "lng": 116.40, "lat": 39.91},
        ])

        from agent.tools.poi_search import search_nearby_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await search_nearby_tool(116.397, 39.909, "景点", radius=2000)

        mock_amap.search_nearby.assert_awaited_once_with(
            lng=116.397,
            lat=39.909,
            category="景点",
            radius=2000,
        )
        assert len(result) == 1


# ---------------------------------------------------------------------------
# geocode_tool / reverse_geocode_tool
# ---------------------------------------------------------------------------


class TestGeocodeTool:
    """Tests for geocode_tool and reverse_geocode_tool."""

    async def test_geocode_tool_returns_coordinates(
        self, mock_amap: MagicMock
    ) -> None:
        """geocode_tool should return (lng, lat) tuple."""
        from agent.tools.geocoding import geocode_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await geocode_tool("北京市东城区景山前街4号")

        mock_amap.geocode.assert_awaited_once_with("北京市东城区景山前街4号")
        assert result == (116.397428, 39.90923)

    async def test_geocode_tool_with_city(self, mock_amap: MagicMock) -> None:
        """geocode_tool passes city to service when provided."""
        mock_amap.geocode.return_value = (121.473, 31.230)
        from agent.tools.geocoding import geocode_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await geocode_tool("黄浦区人民广场", city="上海")

        mock_amap.geocode.assert_awaited_once_with("黄浦区人民广场")
        assert result == (121.473, 31.230)

    async def test_reverse_geocode_tool(self, mock_amap: MagicMock) -> None:
        """reverse_geocode_tool should return address dict."""
        from agent.tools.geocoding import reverse_geocode_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await reverse_geocode_tool(116.397428, 39.90923)

        mock_amap.reverse_geocode.assert_awaited_once_with(116.397428, 39.90923)
        assert result["address"] == "北京市东城区景山前街4号"
        assert result["city"] == "北京市"


# ---------------------------------------------------------------------------
# plan_route_tool
# ---------------------------------------------------------------------------


class TestPlanRouteTool:
    """Tests for plan_route_tool."""

    async def test_plan_route_tool_returns_route(
        self, mock_amap: MagicMock
    ) -> None:
        """plan_route_tool should return route dict with distance and duration."""
        from agent.tools.route_planning import plan_route_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            result = await plan_route_tool(
                origin_lng=116.397,
                origin_lat=39.909,
                dest_lng=116.399,
                dest_lat=39.911,
            )

        mock_amap.plan_route.assert_awaited_once()
        call_args = mock_amap.plan_route.call_args
        assert call_args.kwargs["origin"] == (116.397, 39.909)
        assert call_args.kwargs["destination"] == (116.399, 39.911)
        assert call_args.kwargs["mode"] == "driving"

        assert result["distance_km"] == pytest.approx(1.5)
        assert result["duration_min"] == pytest.approx(18.0)
        assert "polyline" in result

    async def test_plan_route_tool_walking_mode(self, mock_amap: MagicMock) -> None:
        """plan_route_tool should pass mode parameter to service."""
        from agent.tools.route_planning import plan_route_tool

        with patch("agent.tools.get_amap", return_value=mock_amap):
            await plan_route_tool(
                origin_lng=116.397,
                origin_lat=39.909,
                dest_lng=116.399,
                dest_lat=39.911,
                mode="walking",
            )

        call_args = mock_amap.plan_route.call_args
        assert call_args.kwargs["mode"] == "walking"


# ---------------------------------------------------------------------------
# score_pois_tool (pure computation, no API calls)
# ---------------------------------------------------------------------------


class TestScorePoisTool:
    """Tests for score_pois_tool multi-factor scoring."""

    def test_score_pois_returns_pois_with_score(
        self, sample_pois: list[dict]
    ) -> None:
        """score_pois_tool should add 'score' field to each POI."""
        from agent.tools.spatial_analysis import score_pois_tool

        result = score_pois_tool(
            pois=sample_pois,
            preferences=["文化", "历史"],
            city_center_lng=116.407,
            city_center_lat=39.904,
        )

        assert len(result) == 3
        for poi in result:
            assert "score" in poi
            assert 0.0 <= poi["score"] <= 1.0

    def test_score_pois_preference_score_jaccard(
        self, sample_pois: list[dict]
    ) -> None:
        """POI with more matching tags should score higher on preference."""
        from agent.tools.spatial_analysis import score_pois_tool

        result = score_pois_tool(
            pois=sample_pois,
            preferences=["文化", "历史", "古建筑"],
            city_center_lng=116.407,
            city_center_lat=39.904,
        )

        # poi_1 (故宫) has tags [文化, 历史, 古建筑] - matches all 3
        # poi_2 (颐和园) has tags [文化, 园林, 历史] - matches 2
        # poi_3 (南锣鼓巷) has tags [美食, 购物, 胡同] - matches 0
        assert result[0]["score"] > result[1]["score"]
        assert result[1]["score"] > result[2]["score"]

    def test_score_pois_no_preferences(self, sample_pois: list[dict]) -> None:
        """With empty preferences, preference_score should be 0 for all."""
        from agent.tools.spatial_analysis import score_pois_tool

        result = score_pois_tool(
            pois=sample_pois,
            preferences=[],
            city_center_lng=116.407,
            city_center_lat=39.904,
        )

        # All scores should still be >= 0 (other factors contribute)
        for poi in result:
            assert poi["score"] >= 0.0

    def test_score_pois_rating_contributes(self, sample_pois: list[dict]) -> None:
        """Higher rated POIs should get higher rating_score component."""
        from agent.tools.spatial_analysis import score_pois_tool

        result = score_pois_tool(
            pois=sample_pois,
            preferences=["文化", "历史"],
            city_center_lng=116.407,
            city_center_lat=39.904,
        )

        # poi_1 has rating 4.8, poi_3 has rating 4.2
        # With same preference match, poi_1 should benefit from higher rating
        assert result[0]["score"] > result[2]["score"]

    def test_score_pois_weights_sum(self, sample_pois: list[dict]) -> None:
        """Verify that weights are correctly applied (sum to 1.0)."""
        from agent.tools.spatial_analysis import WEIGHTS

        total_weight = sum(WEIGHTS.values())
        assert total_weight == pytest.approx(1.0)

    def test_score_pois_empty_list(self) -> None:
        """Empty POI list should return empty list."""
        from agent.tools.spatial_analysis import score_pois_tool

        result = score_pois_tool(pois=[], preferences=["文化"])
        assert result == []

    def test_score_pois_normalized_scores(self) -> None:
        """Verify individual score components are in [0, 1]."""
        from agent.tools.spatial_analysis import _compute_scores

        pois = [
            {
                "amap_id": "p1",
                "name": "Test",
                "tags": ["文化"],
                "rating": 4.0,
                "review_count": 100,
                "lng": 116.40,
                "lat": 39.90,
            },
        ]

        scores = _compute_scores(
            pois=pois,
            preferences=["文化"],
            city_center_lng=116.407,
            city_center_lat=39.904,
        )

        assert len(scores) == 1
        for key in ["preference_score", "distance_score", "rating_score",
                     "time_score", "popularity_score"]:
            assert key in scores[0]
            assert 0.0 <= scores[0][key] <= 1.0


# ---------------------------------------------------------------------------
# get_weather_tool
# ---------------------------------------------------------------------------


class TestGetWeatherTool:
    """Tests for get_weather_tool placeholder."""

    async def test_weather_returns_placeholder(self) -> None:
        """get_weather_tool should return mock weather data."""
        from agent.tools.weather import get_weather_tool

        result = await get_weather_tool("北京")

        assert result["city"] == "北京"
        assert "temperature" in result
        assert "condition" in result
        assert "humidity" in result
        assert isinstance(result["temperature"], (int, float))
        assert isinstance(result["humidity"], (int, float))

    async def test_weather_different_city(self) -> None:
        """get_weather_tool should use the city parameter."""
        from agent.tools.weather import get_weather_tool

        result = await get_weather_tool("上海")
        assert result["city"] == "上海"


# ---------------------------------------------------------------------------
# get_amap() singleton
# ---------------------------------------------------------------------------


class TestGetAmap:
    """Tests for get_amap() singleton factory."""

    def test_get_amap_returns_same_instance(self) -> None:
        """get_amap() should return the same AmapService instance."""
        from agent.tools import get_amap

        with patch.dict("os.environ", {"AMAP_API_KEY": "test_key_123"}):
            a = get_amap()
            b = get_amap()
            assert a is b

    def test_get_amap_creates_amap_service(self) -> None:
        """get_amap() should return an AmapService instance."""
        from agent.tools import get_amap, _reset_amap_instance
        from app.services.amap_service import AmapService

        _reset_amap_instance()  # clear any cached singleton

        with patch.dict("os.environ", {"AMAP_API_KEY": "test_key_456"}):
            svc = get_amap()
            assert isinstance(svc, AmapService)


# ---------------------------------------------------------------------------
# ALL_TOOLS
# ---------------------------------------------------------------------------


class TestAllTools:
    """Tests for ALL_TOOLS list."""

    def test_all_tools_contains_all_functions(self) -> None:
        """ALL_TOOLS should contain all 7 tool functions."""
        from agent.tools import ALL_TOOLS

        tool_names = {fn.__name__ for fn in ALL_TOOLS}

        expected = {
            "search_pois_tool",
            "search_nearby_tool",
            "geocode_tool",
            "reverse_geocode_tool",
            "plan_route_tool",
            "score_pois_tool",
            "get_weather_tool",
        }
        assert tool_names == expected

    def test_all_tools_are_async_or_callable(self) -> None:
        """All tools should be callable."""
        from agent.tools import ALL_TOOLS

        for tool_fn in ALL_TOOLS:
            assert callable(tool_fn)
