"""Tests for POI search API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.poi import POIResponse


def _make_poi_response(**overrides: object) -> POIResponse:
    """Create a POIResponse with sensible defaults."""
    defaults = {
        "id": 1,
        "name": "西湖",
        "category": "nature",
        "lng": 120.15,
        "lat": 30.25,
        "rating": 4.5,
        "review_count": 500,
        "tags": ["景点", "湖泊"],
    }
    defaults.update(overrides)
    return POIResponse(**defaults)  # type: ignore[arg-type]


class TestPOISearchEndpoint:
    """Test GET /api/v1/poi/search."""

    @patch("app.api.v1.poi.get_session")
    @patch("app.api.v1.poi.search_pois")
    async def test_basic_search(
        self,
        mock_search: MagicMock,
        mock_get_session: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test basic search returns correct envelope."""
        poi = _make_poi_response()
        mock_search.return_value = {"total": 1, "items": [poi]}

        # Make get_session return a mock async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session

        response = await client.get("/api/v1/poi/search", params={"city": "杭州"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["total"] == 1
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["name"] == "西湖"

    @patch("app.api.v1.poi.get_session")
    @patch("app.api.v1.poi.search_pois")
    async def test_query_params_passed(
        self,
        mock_search: MagicMock,
        mock_get_session: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test that query params are correctly forwarded to service."""
        mock_search.return_value = {"total": 0, "items": []}
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session

        await client.get(
            "/api/v1/poi/search",
            params={
                "city": "北京",
                "category": "temple",
                "keyword": "故宫",
                "rating_min": 4.0,
                "page": 2,
                "size": 10,
            },
        )

        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args
        # Check positional/keyword args
        assert call_kwargs.kwargs["city"] == "北京"
        assert call_kwargs.kwargs["category"] == "temple"
        assert call_kwargs.kwargs["keyword"] == "故宫"
        assert call_kwargs.kwargs["rating_min"] == 4.0
        assert call_kwargs.kwargs["page"] == 2
        assert call_kwargs.kwargs["size"] == 10

    @patch("app.api.v1.poi.get_session")
    @patch("app.api.v1.poi.search_pois")
    async def test_bbox_param_parsed(
        self,
        mock_search: MagicMock,
        mock_get_session: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test that bbox string is parsed into floats."""
        mock_search.return_value = {"total": 0, "items": []}
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session

        await client.get(
            "/api/v1/poi/search",
            params={
                "city": "杭州",
                "bbox": "120.0,30.0,120.5,30.5",
            },
        )

        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args
        assert call_kwargs.kwargs["bbox"] == [120.0, 30.0, 120.5, 30.5]

    @patch("app.api.v1.poi.get_session")
    @patch("app.api.v1.poi.search_pois")
    async def test_empty_result(
        self,
        mock_search: MagicMock,
        mock_get_session: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test empty result set returns correct structure."""
        mock_search.return_value = {"total": 0, "items": []}
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session

        response = await client.get("/api/v1/poi/search", params={"city": "未知城市"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    async def test_missing_city_param(self, client: AsyncClient) -> None:
        """Test that missing city param returns 422."""
        response = await client.get("/api/v1/poi/search")
        assert response.status_code == 422

    @patch("app.api.v1.poi.get_session")
    @patch("app.api.v1.poi.search_pois")
    async def test_pagination_defaults(
        self,
        mock_search: MagicMock,
        mock_get_session: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test default pagination values."""
        mock_search.return_value = {"total": 0, "items": []}
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session

        await client.get("/api/v1/poi/search", params={"city": "杭州"})

        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args
        assert call_kwargs.kwargs["page"] == 1
        assert call_kwargs.kwargs["size"] == 20
