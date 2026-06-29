"""Tests for SQLAlchemy ORM models - structure and field verification."""

import pytest
from geoalchemy2 import Geometry
from sqlalchemy import inspect
from sqlalchemy.types import ARRAY
from sqlalchemy.dialects.postgresql import JSONB

from app.models import Base, ChatSession, POI, Trip, TripDay, TripDayPOI, User


class TestBaseModel:
    """Test the shared Base class."""

    def test_base_is_declarative(self) -> None:
        """Base should be a DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)

    def test_all_models_inherit_base(self) -> None:
        """All models should inherit from Base."""
        for model in (POI, User, ChatSession, Trip, TripDay, TripDayPOI):
            assert issubclass(model, Base), f"{model.__name__} does not inherit Base"


class TestPOIModel:
    """Test POI model fields and types."""

    def test_table_name(self) -> None:
        assert POI.__tablename__ == "pois"

    def test_has_required_columns(self) -> None:
        """POI should have all required columns."""
        mapper = inspect(POI)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id",
            "name",
            "category",
            "city",
            "location",
            "rating",
            "tags",
            "description",
            "opening_hours",
            "avg_visit_duration",
            "review_count",
            "extra_data",
            "created_at",
        }
        assert expected.issubset(column_names)

    def test_location_is_geometry_point(self) -> None:
        """location column should be GEOMETRY(POINT, 4326)."""
        mapper = inspect(POI)
        location_col = mapper.columns["location"]
        assert isinstance(location_col.type, Geometry)
        assert location_col.type.geometry_type == "POINT"
        assert location_col.type.srid == 4326

    def test_tags_is_array(self) -> None:
        """tags column should be ARRAY type."""
        mapper = inspect(POI)
        tags_col = mapper.columns["tags"]
        assert isinstance(tags_col.type, ARRAY)

    def test_extra_data_is_jsonb(self) -> None:
        """extra_data should be JSONB type."""
        mapper = inspect(POI)
        extra_col = mapper.columns["extra_data"]
        assert isinstance(extra_col.type, JSONB)

    def test_to_dict_method(self) -> None:
        """POI should have a to_dict() method."""
        assert hasattr(POI, "to_dict")
        assert callable(getattr(POI, "to_dict"))

    def test_to_dict_includes_location(self) -> None:
        """POI.to_dict() should include location field when location is set."""
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point

        poi = POI(
            id=1,
            name="Test POI",
            category="test",
            city="test_city",
            rating=4.5,
        )
        # Set location using geoalchemy2 shape conversion
        poi.location = from_shape(Point(116.397428, 39.90923), srid=4326)

        result = poi.to_dict()

        assert "location" in result
        assert isinstance(result["location"], dict)
        assert result["location"]["lng"] == pytest.approx(116.397428)
        assert result["location"]["lat"] == pytest.approx(39.90923)

    def test_to_dict_location_none(self) -> None:
        """POI.to_dict() should not include location key when location is None."""
        poi = POI(
            id=2,
            name="Test POI No Location",
            category="test",
            city="test_city",
        )

        result = poi.to_dict()

        assert "location" not in result


class TestUserModel:
    """Test User model fields."""

    def test_table_name(self) -> None:
        assert User.__tablename__ == "users"

    def test_has_required_columns(self) -> None:
        mapper = inspect(User)
        column_names = {c.key for c in mapper.columns}
        expected = {"id", "username", "hashed_password", "nickname"}
        assert expected.issubset(column_names)

    def test_username_is_unique(self) -> None:
        mapper = inspect(User)
        username_col = mapper.columns["username"]
        assert username_col.unique is True

    def test_has_relationships(self) -> None:
        """User should have chat_sessions and trips relationships."""
        mapper = inspect(User)
        rel_names = {r.key for r in mapper.relationships}
        assert "chat_sessions" in rel_names
        assert "trips" in rel_names


class TestChatSessionModel:
    """Test ChatSession model fields."""

    def test_table_name(self) -> None:
        assert ChatSession.__tablename__ == "chat_sessions"

    def test_has_required_columns(self) -> None:
        mapper = inspect(ChatSession)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id",
            "user_id",
            "title",
            "messages_json",
            "agent_state_json",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(column_names)

    def test_messages_json_is_jsonb(self) -> None:
        mapper = inspect(ChatSession)
        col = mapper.columns["messages_json"]
        assert isinstance(col.type, JSONB)

    def test_agent_state_json_is_jsonb(self) -> None:
        mapper = inspect(ChatSession)
        col = mapper.columns["agent_state_json"]
        assert isinstance(col.type, JSONB)

    def test_has_user_relationship(self) -> None:
        mapper = inspect(ChatSession)
        rel_names = {r.key for r in mapper.relationships}
        assert "user" in rel_names

    def test_user_id_foreign_key(self) -> None:
        mapper = inspect(ChatSession)
        fk_col = mapper.columns["user_id"]
        fk_targets = {str(fk.target_fullname) for fk in fk_col.foreign_keys}
        assert "users.id" in fk_targets


class TestTripModel:
    """Test Trip model fields."""

    def test_table_name(self) -> None:
        assert Trip.__tablename__ == "trips"

    def test_has_required_columns(self) -> None:
        mapper = inspect(Trip)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id",
            "user_id",
            "title",
            "city",
            "start_date",
            "end_date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(column_names)

    def test_has_user_relationship(self) -> None:
        mapper = inspect(Trip)
        rel_names = {r.key for r in mapper.relationships}
        assert "user" in rel_names

    def test_has_days_relationship(self) -> None:
        mapper = inspect(Trip)
        rel_names = {r.key for r in mapper.relationships}
        assert "days" in rel_names

    def test_days_cascade_delete(self) -> None:
        """Trip.days should cascade delete."""
        mapper = inspect(Trip)
        days_rel = mapper.relationships["days"]
        assert "delete" in days_rel.cascade
        assert "delete-orphan" in days_rel.cascade


class TestTripDayModel:
    """Test TripDay model fields."""

    def test_table_name(self) -> None:
        assert TripDay.__tablename__ == "trip_days"

    def test_has_required_columns(self) -> None:
        mapper = inspect(TripDay)
        column_names = {c.key for c in mapper.columns}
        expected = {"id", "trip_id", "day_number", "date", "notes"}
        assert expected.issubset(column_names)

    def test_has_trip_relationship(self) -> None:
        mapper = inspect(TripDay)
        rel_names = {r.key for r in mapper.relationships}
        assert "trip" in rel_names

    def test_has_pois_relationship(self) -> None:
        mapper = inspect(TripDay)
        rel_names = {r.key for r in mapper.relationships}
        assert "pois" in rel_names

    def test_pois_cascade_delete(self) -> None:
        """TripDay.pois should cascade delete."""
        mapper = inspect(TripDay)
        pois_rel = mapper.relationships["pois"]
        assert "delete" in pois_rel.cascade
        assert "delete-orphan" in pois_rel.cascade


class TestTripDayPOIModel:
    """Test TripDayPOI model fields."""

    def test_table_name(self) -> None:
        assert TripDayPOI.__tablename__ == "trip_day_pois"

    def test_has_required_columns(self) -> None:
        mapper = inspect(TripDayPOI)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id",
            "trip_day_id",
            "poi_id",
            "sort_order",
            "arrival_time",
            "departure_time",
            "score",
            "notes",
        }
        assert expected.issubset(column_names)

    def test_has_trip_day_relationship(self) -> None:
        mapper = inspect(TripDayPOI)
        rel_names = {r.key for r in mapper.relationships}
        assert "trip_day" in rel_names

    def test_trip_day_id_foreign_key(self) -> None:
        mapper = inspect(TripDayPOI)
        fk_col = mapper.columns["trip_day_id"]
        fk_targets = {str(fk.target_fullname) for fk in fk_col.foreign_keys}
        assert "trip_days.id" in fk_targets

    def test_poi_id_foreign_key(self) -> None:
        mapper = inspect(TripDayPOI)
        fk_col = mapper.columns["poi_id"]
        fk_targets = {str(fk.target_fullname) for fk in fk_col.foreign_keys}
        assert "pois.id" in fk_targets


class TestDatabaseModule:
    """Test database module exports."""

    def test_engine_exists(self) -> None:
        from app.database import engine

        assert engine is not None

    def test_session_factory_exists(self) -> None:
        from app.database import async_session_factory

        assert async_session_factory is not None

    def test_get_session_is_callable(self) -> None:
        from app.database import get_session

        assert callable(get_session)
