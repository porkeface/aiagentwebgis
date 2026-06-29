"""Tests for Trip CRUD API endpoints."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from geoalchemy2.elements import WKBElement
from httpx import AsyncClient
from shapely.geometry import Point

from app.api.v1.deps import get_current_user
from app.database import get_session
from app.main import app
from app.models.poi import POI
from app.models.trip import Trip, TripDay, TripDayPOI
from app.schemas.trip import TripCreate


def _make_trip(**overrides):
    """Create a mock Trip ORM instance with sensible defaults."""
    trip = MagicMock(spec=Trip)
    trip.id = overrides.get("id", 1)
    trip.user_id = overrides.get("user_id", 1)
    trip.title = overrides.get("title", "杭州三日游")
    trip.city = overrides.get("city", "杭州")
    trip.start_date = overrides.get("start_date", date.today())
    trip.end_date = overrides.get("end_date", date.today() + timedelta(days=2))
    trip.status = overrides.get("status", "draft")
    trip.notes = overrides.get("notes", None)
    trip.created_at = overrides.get("created_at", datetime.now())
    trip.updated_at = overrides.get("updated_at", datetime.now())
    trip.days = overrides.get("days", [])
    return trip


def _make_mock_poi(poi_id: int, name: str = "POI", lng: float = 120.0, lat: float = 30.0):
    """Create a mock POI with location."""
    poi = MagicMock(spec=POI)
    poi.id = poi_id
    poi.name = name
    poi.category = "景点"
    poi.rating = 4.5
    poi.address = "测试地址"
    poi.tags = ["文化", "历史"]
    # Create a real WKBElement for location
    point = Point(lng, lat)
    poi.location = WKBElement(point.wkb, srid=4326)
    return poi


def _make_trip_day(day_number=1, poi_count=0):
    """Create a mock TripDay with POIs."""
    day = MagicMock(spec=TripDay)
    day.id = day_number
    day.trip_id = 1
    day.day_number = day_number
    day.date = date.today() + timedelta(days=day_number - 1)
    day.notes = None

    pois = []
    for i in range(poi_count):
        daypoi = MagicMock(spec=TripDayPOI)
        daypoi.id = i + 1
        daypoi.trip_day_id = day.id
        daypoi.poi_id = 100 + i
        daypoi.sort_order = i
        daypoi.arrival_time = "09:00"
        daypoi.departure_time = "11:00"
        daypoi.score = 4.5
        daypoi.notes = None
        # Attach a mock POI with proper location
        daypoi.poi = _make_mock_poi(100 + i, f"景点{i+1}", 120.0 + i * 0.01, 30.0 + i * 0.01)
        pois.append(daypoi)

    day.pois = pois
    return day


def _setup_overrides(user_id: int = 1) -> AsyncMock:
    """Set up dependency overrides for auth and session.

    Returns a mock AsyncSession for further configuration.
    """
    mock_session = AsyncMock()

    async def _override_get_session() -> AsyncMock:
        return mock_session

    async def _override_get_current_user() -> int:
        return user_id

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return mock_session


class TestCreateTrip:
    """Test POST /api/v1/trips."""

    @patch("app.services.trip_service.create_trip")
    async def test_create_trip_success(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test successful trip creation."""
        _setup_overrides()
        try:
            trip = _make_trip()
            mock_service.return_value = trip

            payload = {"city": "杭州", "days": 3, "preferences": [], "companion_types": []}
            response = await client.post("/api/v1/trips", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["id"] == 1
            assert data["data"]["city"] == "杭州"
            assert data["data"]["status"] == "draft"
        finally:
            app.dependency_overrides.clear()

    async def test_create_trip_validation_error(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that invalid data returns 422."""
        _setup_overrides()
        try:
            # days must be >= 1
            payload = {"city": "杭州", "days": 0}
            response = await client.post("/api/v1/trips", json=payload)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.trip_service.create_trip")
    async def test_create_trip_sets_dates(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test that service is called with correct date calculations."""
        _setup_overrides()
        try:
            trip = _make_trip()
            mock_service.return_value = trip

            payload = {"city": "北京", "days": 5, "preferences": ["文化"], "companion_types": ["family"]}
            await client.post("/api/v1/trips", json=payload)

            # Verify service was called
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args.kwargs["trip_data"].city == "北京"
            assert call_args.kwargs["trip_data"].days == 5
        finally:
            app.dependency_overrides.clear()


class TestListTrips:
    """Test GET /api/v1/trips."""

    @patch("app.services.trip_service.list_trips")
    async def test_list_trips_success(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test listing trips with pagination."""
        _setup_overrides()
        try:
            trips = [_make_trip(id=1), _make_trip(id=2)]
            mock_service.return_value = {"total": 2, "items": trips}

            response = await client.get("/api/v1/trips")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total"] == 2
            assert len(data["data"]["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.trip_service.list_trips")
    async def test_list_trips_pagination(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test pagination params are forwarded."""
        _setup_overrides()
        try:
            mock_service.return_value = {"total": 0, "items": []}

            await client.get("/api/v1/trips", params={"page": 2, "size": 5})

            mock_service.assert_called_once()
            call_kwargs = mock_service.call_args.kwargs
            assert call_kwargs["page"] == 2
            assert call_kwargs["size"] == 5
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.trip_service.list_trips")
    async def test_list_trips_empty(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test empty trip list."""
        _setup_overrides()
        try:
            mock_service.return_value = {"total": 0, "items": []}

            response = await client.get("/api/v1/trips")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total"] == 0
            assert data["data"]["items"] == []
        finally:
            app.dependency_overrides.clear()


class TestGetTrip:
    """Test GET /api/v1/trips/{trip_id}."""

    @patch("app.services.trip_service.get_trip")
    async def test_get_trip_success(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test getting trip detail."""
        _setup_overrides()
        try:
            day1 = _make_trip_day(day_number=1, poi_count=2)
            day2 = _make_trip_day(day_number=2, poi_count=1)
            trip = _make_trip(days=[day1, day2])
            mock_service.return_value = trip

            response = await client.get("/api/v1/trips/1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == 1
            assert len(data["data"]["daily_plans"]) == 2
            assert len(data["data"]["daily_plans"][0]["pois"]) == 2
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.trip_service.get_trip")
    async def test_get_trip_not_found(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test getting non-existent trip returns 404."""
        _setup_overrides()
        try:
            mock_service.return_value = None

            response = await client.get("/api/v1/trips/999")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestUpdateTrip:
    """Test PUT /api/v1/trips/{trip_id}."""

    @patch("app.services.trip_service.update_trip")
    async def test_update_trip_success(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test successful trip update."""
        _setup_overrides()
        try:
            trip = _make_trip(title="Updated Title")
            mock_service.return_value = trip

            payload = {"title": "Updated Title"}
            response = await client.put("/api/v1/trips/1", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["title"] == "Updated Title"
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.trip_service.update_trip")
    async def test_update_trip_not_found(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test updating non-existent trip returns 404."""
        _setup_overrides()
        try:
            mock_service.return_value = None

            payload = {"title": "Updated"}
            response = await client.put("/api/v1/trips/999", json=payload)
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestDeleteTrip:
    """Test DELETE /api/v1/trips/{trip_id}."""

    @patch("app.services.trip_service.delete_trip")
    async def test_delete_trip_success(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test successful trip deletion."""
        _setup_overrides()
        try:
            mock_service.return_value = True

            response = await client.delete("/api/v1/trips/1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["deleted"] is True
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.trip_service.delete_trip")
    async def test_delete_trip_not_found(
        self,
        mock_service: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Test deleting non-existent trip returns 404."""
        _setup_overrides()
        try:
            mock_service.return_value = False

            response = await client.delete("/api/v1/trips/999")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
