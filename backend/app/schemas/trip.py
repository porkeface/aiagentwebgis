"""Trip-related Pydantic schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    """Request schema for creating a trip."""

    city: str
    days: int = Field(ge=1, le=30)
    title: str | None = None
    preferences: list[str] = Field(default_factory=list)
    companion_types: list[str] = Field(default_factory=list)


class TripResponse(BaseModel):
    """Response schema for a trip summary."""

    id: int
    city: str
    days: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TripDayPOIDetail(BaseModel):
    """POI detail within a day plan."""

    poi_id: int
    sort_order: int
    arrival_time: str | None = None
    departure_time: str | None = None
    score: float | None = None
    notes: str | None = None
    name: str | None = None
    category: str | None = None
    lng: float | None = None
    lat: float | None = None

    model_config = {"from_attributes": True}


class DayPlanDetail(BaseModel):
    """A single day plan with its POIs."""

    day_number: int
    date: date
    notes: str | None = None
    pois: list[TripDayPOIDetail] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TripDetailResponse(BaseModel):
    """Detailed trip response including daily plans."""

    id: int
    city: str
    days: int
    status: str
    created_at: datetime
    daily_plans: list[DayPlanDetail] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Plan-save schemas (AI plan → persisted Trip) ─────────────────────────
#
# These are used by POST /api/v1/trips/save-plan which takes the AI planner
# output (daily_plans + route data) and materialises it as a Trip with
# TripDay + TripDayPOI rows.

class SavePlanPOI(BaseModel):
    """A POI stop inside an AI-generated daily plan."""

    id: int | str = Field(description="POI database id (int) or Amap id (str)")
    name: str = ""
    category: str = ""
    lng: float = 0.0
    lat: float = 0.0
    rating: float | None = None
    address: str | None = None
    tags: list[str] = Field(default_factory=list)
    photo: str | None = None
    description: str | None = None


class SavePlanDay(BaseModel):
    """A single day inside a save-plan request."""

    day: int = Field(ge=1, le=30)
    day_title: str | None = None
    pois: list[SavePlanPOI] = Field(default_factory=list)
    total_distance_km: float = 0.0
    total_duration_min: float | None = None
    polyline: str | None = None
    segments: list[dict] = Field(default_factory=list)


class SavePlanRequest(BaseModel):
    """POST /api/v1/trips/save-plan body."""

    city: str
    days: int = Field(ge=1, le=30)
    title: str | None = None
    daily_plans: list[SavePlanDay] = Field(default_factory=list)

