"""Pydantic schemas for API request/response validation."""

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

__all__ = [
    "POIResponse",
    "POISearchRequest",
    "TripCreate",
    "TripResponse",
    "TripDetailResponse",
    "DayPlanDetail",
    "TripDayPOIDetail",
    "ChatRequest",
    "ChatSSEEvent",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
]
