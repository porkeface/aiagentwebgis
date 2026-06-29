"""Spatial filter using PostGIS ST_DWithin for POI proximity queries."""

from __future__ import annotations

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.poi import POI


async def _get_session():
    """Return an async session (for testability via patching)."""
    return async_session_factory()


async def spatial_filter_pois(
    city: str,
    center_lng: float,
    center_lat: float,
    radius_km: float = 10.0,
    min_count: int = 10,
) -> tuple[list[dict], bool]:
    """Query POIs within radius using PostGIS spatial filter.

    Args:
        city: City name to filter by.
        center_lng: Center longitude (EPSG:4326).
        center_lat: Center latitude (EPSG:4326).
        radius_km: Search radius in kilometers (default 10.0).
        min_count: Minimum POI count threshold (default 10).

    Returns:
        (pois, needs_api_supplement) tuple where:
        - pois: List of POI dicts within radius
        - needs_api_supplement: True if len(pois) < min_count

    The radius is converted to degrees approximately: radius_degrees = radius_km / 111.0
    Uses ST_DWithin for efficient spatial indexing.
    """
    # Convert km to approximate degrees (1 degree ~ 111 km)
    radius_degrees = radius_km / 111.0

    # Build spatial query
    # ST_DWithin(POI.location, ST_SetSRID(ST_MakePoint(lng, lat), 4326), radius_degrees)
    center_point = func.ST_SetSRID(func.ST_MakePoint(center_lng, center_lat), 4326)

    stmt = (
        select(POI)
        .where(POI.city == city)
        .where(func.ST_DWithin(POI.location, center_point, radius_degrees))
    )

    # Execute query using async session factory
    session = await _get_session()
    async with session:
        result = await session.execute(stmt)
        poi_rows = result.scalars().all()

    # Convert to dicts
    pois = [poi.to_dict() for poi in poi_rows]

    # Check if supplement needed
    needs_api_supplement = len(pois) < min_count

    return pois, needs_api_supplement
