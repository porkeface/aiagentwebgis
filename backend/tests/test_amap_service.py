"""Tests for AmapService - POI search, geocoding, and route planning.

All httpx responses are mocked to avoid real API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.amap_service import AmapService


@pytest.fixture
def api_key() -> str:
    """Provide a test API key."""
    return "test_amap_api_key_12345"


@pytest.fixture
def service(api_key: str) -> AmapService:
    """Provide an AmapService instance with test key."""
    return AmapService(api_key=api_key)


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with the given JSON payload."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://restapi.amap.com/v3/test"),
    )


# ---------------------------------------------------------------------------
# search_pois
# ---------------------------------------------------------------------------


class TestSearchPois:
    """Tests for AmapService.search_pois."""

    async def test_search_pois_returns_list(self, service: AmapService) -> None:
        """Mock response with 1 POI, verify parsing."""
        mock_data = {
            "status": "1",
            "count": "1",
            "info": "OK",
            "pois": [
                {
                    "id": "B000A7BD6C",
                    "name": "故宫博物院",
                    "type": "风景名胜;风景名胜",
                    "address": "北京市东城区景山前街4号",
                    "location": "116.397428,39.90923",
                    "city": [
                        {"cityname": "北京市"},
                    ],
                },
            ],
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            results = await service.search_pois(city="北京", keyword="故宫")

        assert isinstance(results, list)
        assert len(results) == 1
        poi = results[0]
        assert poi["name"] == "故宫博物院"
        assert poi["lng"] == pytest.approx(116.397428)
        assert poi["lat"] == pytest.approx(39.90923)
        assert poi["amap_id"] == "B000A7BD6C"
        assert poi["address"] == "北京市东城区景山前街4号"

    async def test_search_pois_handles_empty(self, service: AmapService) -> None:
        """Mock empty response, verify returns []."""
        mock_data = {
            "status": "1",
            "count": "0",
            "info": "OK",
            "pois": [],
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            results = await service.search_pois(city="北京", keyword="不存在的地点")

        assert results == []

    async def test_search_pois_injects_key_and_params(
        self, service: AmapService
    ) -> None:
        """Verify that key, city, and keyword are passed to the API."""
        mock_data = {"status": "1", "count": "0", "info": "OK", "pois": []}

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            await service.search_pois(city="上海", keyword="外滩", category="景点", limit=5)

        mock_client.get.assert_awaited_once()
        call_args = mock_client.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        params = call_args.kwargs.get("params", {})
        assert "place/text" in url
        assert params["key"] == "test_amap_api_key_12345"
        assert params["city"] == "上海"
        assert params["keywords"] == "外滩"
        assert params["types"] == "景点"
        assert params["offset"] == "5"


# ---------------------------------------------------------------------------
# geocode
# ---------------------------------------------------------------------------


class TestGeocode:
    """Tests for AmapService.geocode."""

    async def test_geocode_returns_coordinates(self, service: AmapService) -> None:
        """Mock geocode response, verify (lng, lat) tuple."""
        mock_data = {
            "status": "1",
            "count": "1",
            "info": "OK",
            "geocodes": [
                {
                    "formatted_address": "北京市东城区景山前街4号",
                    "province": "北京市",
                    "city": "北京市",
                    "district": "东城区",
                    "location": "116.397428,39.90923",
                },
            ],
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            result = await service.geocode("北京市东城区景山前街4号")

        assert isinstance(result, tuple)
        assert len(result) == 2
        lng, lat = result
        assert lng == pytest.approx(116.397428)
        assert lat == pytest.approx(39.90923)

    async def test_geocode_empty_result_raises(self, service: AmapService) -> None:
        """Empty geocode result should raise ValueError."""
        mock_data = {
            "status": "1",
            "count": "0",
            "info": "OK",
            "geocodes": [],
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            with pytest.raises(ValueError, match="No geocode result"):
                await service.geocode("不存在的地方")


# ---------------------------------------------------------------------------
# reverse_geocode
# ---------------------------------------------------------------------------


class TestReverseGeocode:
    """Tests for AmapService.reverse_geocode."""

    async def test_reverse_geocode_returns_address(
        self, service: AmapService
    ) -> None:
        """Mock reverse geocode, verify address and city."""
        mock_data = {
            "status": "1",
            "info": "OK",
            "regeocode": {
                "formatted_address": "北京市东城区景山前街4号",
                "addressComponent": {
                    "province": "北京市",
                    "city": "北京市",
                    "district": "东城区",
                },
            },
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            result = await service.reverse_geocode(116.397428, 39.90923)

        assert isinstance(result, dict)
        assert result["address"] == "北京市东城区景山前街4号"
        assert result["city"] == "北京市"


# ---------------------------------------------------------------------------
# plan_route
# ---------------------------------------------------------------------------


class TestPlanRoute:
    """Tests for AmapService.plan_route."""

    async def test_plan_route_returns_polyline(self, service: AmapService) -> None:
        """Mock route response, verify distance_km, duration_min, polyline."""
        mock_data = {
            "status": "1",
            "info": "OK",
            "route": {
                "paths": [
                    {
                        "distance": "1500",
                        "duration": "1080",
                        "steps": [
                            {
                                "instruction": "向东北步行100米",
                                "polyline": "116.397,39.909;116.398,39.910",
                            },
                            {
                                "instruction": "向东南步行200米",
                                "polyline": "116.398,39.910;116.399,39.911",
                            },
                        ],
                    },
                ],
            },
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            result = await service.plan_route(
                origin=(116.397428, 39.90923),
                destination=(116.399, 39.911),
            )

        assert isinstance(result, dict)
        # distance: 1500m = 1.5km
        assert result["distance_km"] == pytest.approx(1.5)
        # duration: 1080s = 18min
        assert result["duration_min"] == pytest.approx(18.0)
        # polyline should be concatenated from steps
        assert "116.397,39.909;116.398,39.910" in result["polyline"]
        assert "116.398,39.910;116.399,39.911" in result["polyline"]

    async def test_plan_route_driving_mode(self, service: AmapService) -> None:
        """Verify mode parameter is passed to the API URL."""
        mock_data = {
            "status": "1",
            "info": "OK",
            "route": {
                "paths": [
                    {
                        "distance": "5000",
                        "duration": "600",
                        "steps": [
                            {"polyline": "116.397,39.909;116.400,39.912"},
                        ],
                    },
                ],
            },
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_mock_response(mock_data))

        with patch.object(service, "_get_client", return_value=mock_client):
            result = await service.plan_route(
                origin=(116.397428, 39.90923),
                destination=(116.400, 39.912),
                mode="driving",
            )

        call_args = mock_client.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "direction/driving" in url
        assert result["distance_km"] == pytest.approx(5.0)
        assert result["duration_min"] == pytest.approx(10.0)
