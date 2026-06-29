"""POI-related Pydantic schemas."""

from pydantic import BaseModel, Field


class POIResponse(BaseModel):
    """Response schema for a single POI."""

    id: int
    name: str
    category: str
    address: str | None = None
    lng: float
    lat: float
    rating: float | None = None
    review_count: int | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class POISearchRequest(BaseModel):
    """Request schema for POI search."""

    city: str
    category: str | None = None
    keyword: str | None = None
    bbox: str | None = None
    rating_min: float | None = Field(default=None, ge=0.0, le=5.0)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
