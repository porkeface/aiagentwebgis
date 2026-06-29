"""Trip-related Pydantic schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    """Request schema for creating a trip."""

    city: str
    days: int = Field(ge=1, le=30)
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
