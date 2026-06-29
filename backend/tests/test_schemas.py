"""Tests for Pydantic schemas."""

from datetime import datetime

import pytest

from app.schemas.agent import ChatRequest, ChatSSEEvent
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.poi import POIResponse, POISearchRequest
from app.schemas.trip import (
    DayPlanDetail,
    TripCreate,
    TripDayPOIDetail,
    TripDetailResponse,
    TripResponse,
)


# ── POI Schemas ──────────────────────────────────────────────


class TestPOIResponse:
    def test_basic_creation(self) -> None:
        poi = POIResponse(
            id=1, name="西湖", category="nature", lng=120.15, lat=30.25
        )
        assert poi.id == 1
        assert poi.tags == []
        assert poi.rating is None

    def test_with_all_fields(self) -> None:
        poi = POIResponse(
            id=2,
            name="灵隐寺",
            category="temple",
            address="杭州市西湖区",
            lng=120.10,
            lat=30.24,
            rating=4.5,
            review_count=1200,
            tags=["寺庙", "佛教"],
        )
        assert poi.review_count == 1200
        assert len(poi.tags) == 2


class TestPOISearchRequest:
    def test_defaults(self) -> None:
        req = POISearchRequest(city="杭州")
        assert req.page == 1
        assert req.size == 20
        assert req.category is None

    def test_rating_min_validation(self) -> None:
        with pytest.raises(Exception):
            POISearchRequest(city="杭州", rating_min=6.0)

    def test_page_min_validation(self) -> None:
        with pytest.raises(Exception):
            POISearchRequest(city="杭州", page=0)

    def test_size_max_validation(self) -> None:
        with pytest.raises(Exception):
            POISearchRequest(city="杭州", size=200)


# ── Trip Schemas ─────────────────────────────────────────────


class TestTripCreate:
    def test_basic_creation(self) -> None:
        trip = TripCreate(city="杭州", days=3)
        assert trip.preferences == []
        assert trip.companion_types == []

    def test_days_validation(self) -> None:
        with pytest.raises(Exception):
            TripCreate(city="杭州", days=0)

    def test_with_preferences(self) -> None:
        trip = TripCreate(
            city="北京",
            days=5,
            preferences=["文化", "美食"],
            companion_types=["family"],
        )
        assert len(trip.preferences) == 2


class TestTripResponse:
    def test_creation(self) -> None:
        trip = TripResponse(
            id=1,
            city="杭州",
            days=3,
            status="draft",
            created_at=datetime(2026, 1, 1),
        )
        assert trip.status == "draft"


class TestTripDetailResponse:
    def test_with_daily_plans(self) -> None:
        detail = TripDetailResponse(
            id=1,
            city="杭州",
            days=2,
            status="draft",
            created_at=datetime(2026, 1, 1),
            daily_plans=[
                DayPlanDetail(
                    day_number=1,
                    date="2026-07-01",
                    pois=[
                        TripDayPOIDetail(
                            poi_id=10,
                            sort_order=0,
                            name="西湖",
                            category="nature",
                            lng=120.15,
                            lat=30.25,
                        ),
                    ],
                ),
                DayPlanDetail(
                    day_number=2,
                    date="2026-07-02",
                    pois=[],
                ),
            ],
        )
        assert len(detail.daily_plans) == 2
        assert detail.daily_plans[0].pois[0].name == "西湖"
        assert detail.daily_plans[1].pois == []


# ── Agent Schemas ────────────────────────────────────────────


class TestChatRequest:
    def test_without_session(self) -> None:
        req = ChatRequest(message="推荐杭州景点")
        assert req.session_id is None

    def test_with_session(self) -> None:
        req = ChatRequest(message="继续", session_id="abc-123")
        assert req.session_id == "abc-123"


class TestChatSSEEvent:
    def test_valid_types(self) -> None:
        for t in [
            "thinking",
            "tool_calling",
            "poi_result",
            "route_result",
            "plan_summary",
            "text",
            "error",
        ]:
            evt = ChatSSEEvent(type=t, data={"foo": "bar"})
            assert evt.type == t

    def test_invalid_type(self) -> None:
        with pytest.raises(Exception):
            ChatSSEEvent(type="invalid_type", data={})


# ── Auth Schemas ─────────────────────────────────────────────


class TestRegisterRequest:
    def test_valid(self) -> None:
        req = RegisterRequest(
            username="testuser", password="secret123", email="test@example.com"
        )
        assert req.email == "test@example.com"

    def test_password_too_short(self) -> None:
        with pytest.raises(Exception):
            RegisterRequest(username="user", password="123", email="a@b.com")

    def test_username_too_short(self) -> None:
        with pytest.raises(Exception):
            RegisterRequest(username="ab", password="123456", email="a@b.com")

    def test_invalid_email(self) -> None:
        with pytest.raises(Exception):
            RegisterRequest(username="user1", password="123456", email="notanemail")

    def test_email_lowercased(self) -> None:
        req = RegisterRequest(
            username="testuser", password="secret123", email="Test@Example.COM"
        )
        assert req.email == "test@example.com"


class TestLoginRequest:
    def test_creation(self) -> None:
        req = LoginRequest(username="user", password="pass")
        assert req.username == "user"


class TestTokenResponse:
    def test_default_token_type(self) -> None:
        resp = TokenResponse(access_token="abc.def.ghi")
        assert resp.token_type == "bearer"

    def test_custom_token_type(self) -> None:
        resp = TokenResponse(access_token="token", token_type="jwt")
        assert resp.token_type == "jwt"
