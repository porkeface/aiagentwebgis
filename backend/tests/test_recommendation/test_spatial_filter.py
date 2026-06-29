"""Tests for Spatial Filter (Task 3.1).

Tests cover:
- spatial_filter_pois returns POIs within radius
- spatial_filter_pois sets needs_api_supplement when results < min_count
- spatial_filter_pois handles empty results correctly
- spatial query uses ST_DWithin with correct parameters
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_poi(
    id: int,
    name: str,
    category: str,
    city: str,
    lng: float,
    lat: float,
) -> MagicMock:
    """Create a mock POI with to_dict() returning proper dict."""
    poi = MagicMock()
    poi.to_dict.return_value = {
        "id": id,
        "name": name,
        "category": category,
        "city": city,
        "rating": 4.5,
        "tags": ["景点"],
        "description": f"{name} 描述",
        "opening_hours": "08:00-18:00",
        "avg_visit_duration": 120,
        "review_count": 100,
        "extra_data": None,
        "created_at": None,
        "location": {"lng": lng, "lat": lat},
    }
    return poi


# ---------------------------------------------------------------------------
# test_spatial_filter_returns_pois_within_radius
# ---------------------------------------------------------------------------


class TestSpatialFilterReturnsPois:
    """spatial_filter_pois should return POIs found in DB and flag if supplement needed."""

    async def test_spatial_filter_returns_pois_within_radius(
        self,
    ) -> None:
        """Mock returns 5 POIs, verify result has 5 POIs as dicts."""
        from recommendation.spatial_filter import spatial_filter_pois

        mock_pois = [
            _make_mock_poi(1, "故宫博物院", "景点", "北京", 116.397, 39.909),
            _make_mock_poi(2, "景山公园", "景点", "北京", 116.397, 39.925),
            _make_mock_poi(3, "北海公园", "景点", "北京", 116.389, 39.925),
            _make_mock_poi(4, "王府井", "购物", "北京", 116.410, 39.915),
            _make_mock_poi(5, "南锣鼓巷", "景点", "北京", 116.403, 39.937),
        ]

        # Mock session.execute returns rows
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_pois

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "recommendation.spatial_filter._get_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            pois, needs_supplement = await spatial_filter_pois(
                city="北京",
                center_lng=116.407,
                center_lat=39.904,
                radius_km=5.0,
                min_count=3,
            )

        assert len(pois) == 5
        assert needs_supplement is False

        # Verify each poi is a dict with expected fields
        for poi_dict in pois:
            assert isinstance(poi_dict, dict)
            assert "id" in poi_dict
            assert "name" in poi_dict
            assert "location" in poi_dict
            assert "lng" in poi_dict["location"]
            assert "lat" in poi_dict["location"]

    async def test_spatial_filter_supplement_flag_when_below_min_count(self) -> None:
        """When results < min_count, needs_api_supplement should be True."""
        from recommendation.spatial_filter import spatial_filter_pois

        mock_pois = [
            _make_mock_poi(1, "故宫博物院", "景点", "北京", 116.397, 39.909),
            _make_mock_poi(2, "景山公园", "景点", "北京", 116.397, 39.925),
        ]

        # Only 2 POIs found, but min_count is 10
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_pois

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "recommendation.spatial_filter._get_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            pois, needs_supplement = await spatial_filter_pois(
                city="北京",
                center_lng=116.407,
                center_lat=39.904,
                radius_km=5.0,
                min_count=10,
            )

        assert len(pois) == 2
        assert needs_supplement is True


# ---------------------------------------------------------------------------
# test_spatial_filter_excludes_pois_outside_radius
# ---------------------------------------------------------------------------


class TestSpatialFilterQueryConstruction:
    """Verify the spatial query is constructed correctly with ST_DWithin."""

    async def test_spatial_filter_excludes_pois_outside_radius(self) -> None:
        """Verify query uses ST_DWithin with city filter."""
        from recommendation.spatial_filter import spatial_filter_pois

        # Mock session returns empty (simulating no POIs in radius)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "recommendation.spatial_filter._get_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch("recommendation.spatial_filter.select") as mock_select,
        ):
            # Make select().where() chainable
            mock_statement = MagicMock()
            mock_select.return_value = mock_statement
            mock_statement.where.return_value = mock_statement

            await spatial_filter_pois(
                city="北京",
                center_lng=116.407,
                center_lat=39.904,
                radius_km=10.0,
            )

        # Verify select was called with POI model
        mock_select.assert_called_once()

        # Verify where was called (city filter + spatial filter)
        assert mock_statement.where.call_count == 2

        # Verify execute was called with the statement
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# test_spatial_filter_empty_city_returns_empty
# ---------------------------------------------------------------------------


class TestSpatialFilterEmptyCity:
    """When city has no POIs, should return empty list with needs_api_supplement=True."""

    async def test_spatial_filter_empty_city_returns_empty(self) -> None:
        """Mock returns 0 POIs, verify needs_api_supplement=True."""
        from recommendation.spatial_filter import spatial_filter_pois

        # Mock session returns empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "recommendation.spatial_filter._get_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            pois, needs_supplement = await spatial_filter_pois(
                city="小城市",
                center_lng=100.0,
                center_lat=30.0,
                radius_km=10.0,
                min_count=10,
            )

        assert pois == []
        assert needs_supplement is True

    async def test_spatial_filter_default_min_count(self) -> None:
        """Default min_count is 10; 10 results should NOT trigger supplement."""
        from recommendation.spatial_filter import spatial_filter_pois

        # Create exactly 10 mock POIs
        mock_pois = [
            _make_mock_poi(i, f"景点{i}", "景点", "北京", 116.4 + i * 0.01, 39.9)
            for i in range(10)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_pois

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "recommendation.spatial_filter._get_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            pois, needs_supplement = await spatial_filter_pois(
                city="北京",
                center_lng=116.407,
                center_lat=39.904,
            )

        assert len(pois) == 10
        # 10 >= 10 (default min_count), so no supplement needed
        assert needs_supplement is False

    async def test_spatial_filter_radius_conversion(self) -> None:
        """Verify radius_km is converted to degrees correctly (radius_km / 111.0)."""
        from recommendation import spatial_filter as sf_module

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock the select chain to avoid real SQLAlchemy execution
        mock_stmt = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "recommendation.spatial_filter._get_session",
                new_callable=AsyncMock,
                return_value=mock_session,
            ),
            patch.object(sf_module, "select", return_value=mock_stmt),
            patch.object(sf_module, "func") as mock_func,
        ):
            mock_stmt.where.return_value = mock_stmt

            # Set up func mocks
            mock_func.ST_MakePoint.return_value = "mock_point"
            mock_func.ST_SetSRID.return_value = "mock_srid_point"
            mock_func.ST_DWithin.return_value = "mock_dwithin"

            await sf_module.spatial_filter_pois(
                city="北京",
                center_lng=116.407,
                center_lat=39.904,
                radius_km=22.2,
            )

        # Verify ST_MakePoint called with correct lng, lat
        mock_func.ST_MakePoint.assert_called_once_with(116.407, 39.904)

        # Verify ST_SetSRID called with 4326
        mock_func.ST_SetSRID.assert_called_once_with("mock_point", 4326)

        # Verify ST_DWithin called with radius_degrees = 22.2 / 111.0 = 0.2
        expected_radius_degrees = pytest.approx(22.2 / 111.0)
        mock_func.ST_DWithin.assert_called_once()
        call_args = mock_func.ST_DWithin.call_args
        # The third positional arg should be the radius in degrees
        assert call_args[0][2] == expected_radius_degrees
