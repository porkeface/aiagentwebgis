"""Unit tests for trip_service module."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip, TripDay, TripDayPOI
from app.schemas.trip import TripCreate
from app.services import trip_service


def _mock_db_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestCreateTrip:
    """Tests for create_trip function."""

    async def test_create_trip_basic(self) -> None:
        """Test basic trip creation."""
        mock_db = _mock_db_session()

        # Mock the trip creation and query result
        mock_trip = MagicMock(spec=Trip)
        mock_trip.id = 1
        mock_trip.user_id = 1
        mock_trip.title = "杭州 3日游"
        mock_trip.city = "杭州"
        mock_trip.start_date = date.today()
        mock_trip.end_date = date.today() + timedelta(days=2)
        mock_trip.status = "draft"
        mock_trip.days = []

        # Mock execute to return the trip
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_trip
        mock_db.execute.return_value = mock_result

        trip_data = TripCreate(city="杭州", days=3, preferences=[], companion_types=[])
        result = await trip_service.create_trip(mock_db, user_id=1, trip_data=trip_data)

        assert result.id == 1
        assert result.city == "杭州"
        assert result.status == "draft"

        # Verify db.add was called
        assert mock_db.add.called

    async def test_create_trip_calculates_dates(self) -> None:
        """Test that trip dates are calculated correctly."""
        mock_db = _mock_db_session()

        mock_trip = MagicMock(spec=Trip)
        mock_trip.id = 1
        mock_trip.days = []

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_trip
        mock_db.execute.return_value = mock_result

        trip_data = TripCreate(city="北京", days=5, preferences=[], companion_types=[])
        result = await trip_service.create_trip(mock_db, user_id=1, trip_data=trip_data)

        # Verify date range
        assert result.start_date == date.today()
        assert result.end_date == date.today() + timedelta(days=4)


class TestGetTrip:
    """Tests for get_trip function."""

    async def test_get_trip_found(self) -> None:
        """Test getting an existing trip."""
        mock_db = _mock_db_session()

        mock_trip = MagicMock(spec=Trip)
        mock_trip.id = 1
        mock_trip.user_id = 1
        mock_trip.city = "杭州"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_trip
        mock_db.execute.return_value = mock_result

        result = await trip_service.get_trip(mock_db, trip_id=1, user_id=1)

        assert result is not None
        assert result.id == 1
        assert result.city == "杭州"

    async def test_get_trip_not_found(self) -> None:
        """Test getting a non-existent trip."""
        mock_db = _mock_db_session()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await trip_service.get_trip(mock_db, trip_id=999, user_id=1)

        assert result is None

    async def test_get_trip_wrong_user(self) -> None:
        """Test getting a trip owned by another user."""
        mock_db = _mock_db_session()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await trip_service.get_trip(mock_db, trip_id=1, user_id=2)

        assert result is None


class TestListTrips:
    """Tests for list_trips function."""

    async def test_list_trips_empty(self) -> None:
        """Test listing trips when none exist."""
        mock_db = _mock_db_session()

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # Mock list query
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        result = await trip_service.list_trips(mock_db, user_id=1, page=1, size=20)

        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_trips_with_results(self) -> None:
        """Test listing trips with results."""
        mock_db = _mock_db_session()

        mock_trip1 = MagicMock(spec=Trip)
        mock_trip1.id = 1
        mock_trip1.city = "杭州"

        mock_trip2 = MagicMock(spec=Trip)
        mock_trip2.id = 2
        mock_trip2.city = "北京"

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        # Mock list query
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [mock_trip1, mock_trip2]

        mock_db.execute.side_effect = [count_result, list_result]

        result = await trip_service.list_trips(mock_db, user_id=1, page=1, size=20)

        assert result["total"] == 2
        assert len(result["items"]) == 2

    async def test_list_trips_pagination(self) -> None:
        """Test listing trips with pagination."""
        mock_db = _mock_db_session()

        count_result = MagicMock()
        count_result.scalar.return_value = 50

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        result = await trip_service.list_trips(mock_db, user_id=1, page=2, size=10)

        # Verify pagination parameters were used
        assert result["total"] == 50


class TestUpdateTrip:
    """Tests for update_trip function."""

    async def test_update_trip_success(self) -> None:
        """Test successfully updating a trip."""
        mock_db = _mock_db_session()

        mock_trip = MagicMock(spec=Trip)
        mock_trip.id = 1
        mock_trip.user_id = 1
        mock_trip.title = "原标题"
        mock_trip.status = "draft"
        mock_trip.notes = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_trip
        mock_db.execute.return_value = mock_result

        updates = {"title": "新标题", "status": "planned"}
        result = await trip_service.update_trip(mock_db, trip_id=1, user_id=1, updates=updates)

        assert result is not None
        assert mock_trip.title == "新标题"
        assert mock_trip.status == "planned"

    async def test_update_trip_not_found(self) -> None:
        """Test updating a non-existent trip."""
        mock_db = _mock_db_session()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        updates = {"title": "新标题"}
        result = await trip_service.update_trip(mock_db, trip_id=999, user_id=1, updates=updates)

        assert result is None

    async def test_update_trip_ignores_unsafe_fields(self) -> None:
        """Test that unsafe fields are ignored."""
        mock_db = _mock_db_session()

        mock_trip = MagicMock(spec=Trip)
        mock_trip.id = 1
        mock_trip.user_id = 1
        mock_trip.title = "原标题"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_trip
        mock_db.execute.return_value = mock_result

        # Try to update user_id (should be ignored)
        updates = {"user_id": 999, "title": "新标题"}
        result = await trip_service.update_trip(mock_db, trip_id=1, user_id=1, updates=updates)

        # user_id should not be changed
        assert result.user_id != 999


class TestDeleteTrip:
    """Tests for delete_trip function."""

    async def test_delete_trip_success(self) -> None:
        """Test successfully deleting a trip."""
        mock_db = _mock_db_session()

        mock_trip = MagicMock(spec=Trip)
        mock_trip.id = 1
        mock_trip.user_id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_trip
        mock_db.execute.return_value = mock_result

        result = await trip_service.delete_trip(mock_db, trip_id=1, user_id=1)

        assert result is True
        assert mock_db.delete.called

    async def test_delete_trip_not_found(self) -> None:
        """Test deleting a non-existent trip."""
        mock_db = _mock_db_session()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await trip_service.delete_trip(mock_db, trip_id=999, user_id=1)

        assert result is False
        assert not mock_db.delete.called
