"""POI service layer with search and spatial filtering."""

from __future__ import annotations

from typing import Any

from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.poi import POI
from app.schemas.poi import POIResponse


def _poi_to_response(poi: POI) -> POIResponse:
    """Convert a POI ORM instance to a POIResponse schema.

    Handles the PostGIS geometry -> lng/lat conversion.
    """
    lng = 0.0
    lat = 0.0
    if poi.location is not None:
        point = to_shape(poi.location)
        lng = point.x
        lat = point.y

    return POIResponse(
        id=poi.id,
        name=poi.name,
        category=poi.category,
        address=None,
        lng=lng,
        lat=lat,
        rating=poi.rating,
        review_count=poi.review_count,
        tags=poi.tags or [],
    )


async def search_pois(
    db: AsyncSession,
    city: str,
    category: str | None = None,
    keyword: str | None = None,
    bbox: list[float] | None = None,
    rating_min: float | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Search POIs with filters and pagination.

    Args:
        db: Async database session.
        city: City name (required).
        category: Optional category filter.
        keyword: Optional keyword search on name/description.
        bbox: Optional bounding box [min_lng, min_lat, max_lng, max_lat].
        rating_min: Optional minimum rating filter.
        page: Page number (1-indexed, default 1).
        size: Page size (default 20).

    Returns:
        {"total": int, "items": list[POIResponse]}
    """
    # Build base query
    stmt = select(POI).where(POI.city == city)

    # Category filter
    if category is not None:
        stmt = stmt.where(POI.category == category)

    # Keyword filter (search name and description)
    if keyword is not None:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            POI.name.ilike(pattern) | POI.description.ilike(pattern)
        )

    # Bounding box spatial filter
    if bbox is not None and len(bbox) == 4:
        min_lng, min_lat, max_lng, max_lat = bbox
        bbox_geom = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
        stmt = stmt.where(func.ST_Within(POI.location, bbox_geom))

    # Minimum rating filter
    if rating_min is not None:
        stmt = stmt.where(POI.rating >= rating_min)

    # Count total before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * size
    stmt = stmt.offset(offset).limit(size)

    # Execute query
    result = await db.execute(stmt)
    poi_rows = result.scalars().all()

    # Convert to response schemas
    items = [_poi_to_response(poi) for poi in poi_rows]

    return {"total": total, "items": items}
