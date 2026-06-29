"""POI search tool functions — wraps AmapService.search_pois / place-around.

Includes fallback to local database when Amap API fails.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def search_pois_tool(
    city: str,
    category: str,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    """Search POIs by city, category, and optional keyword.

    Tries Amap API first; falls back to local database on failure.

    Args:
        city: City name, e.g. "北京".
        category: POI type category, e.g. "景点".
        keyword: Optional search keyword, e.g. "故宫".

    Returns:
        List of POI dicts from AmapService or local DB fallback.
    """
    from agent.tools import get_amap

    amap = get_amap()
    try:
        return await amap.search_pois(city=city, category=category, keyword=keyword)
    except Exception as e:
        logger.warning(
            f"Amap API search_pois failed for city={city}, category={category}: {e}. "
            "Falling back to local database."
        )
        return await _fallback_db_search(city=city, category=category, keyword=keyword)


async def search_nearby_tool(
    lng: float,
    lat: float,
    category: str,
    radius: int = 1000,
) -> list[dict[str, Any]]:
    """Search nearby POIs around a coordinate.

    Tries Amap API first; falls back to empty list with warning on failure.

    Args:
        lng: Longitude of the center point.
        lat: Latitude of the center point.
        category: POI type category, e.g. "景点".
        radius: Search radius in meters (default 1000).

    Returns:
        List of nearby POI dicts.
    """
    from agent.tools import get_amap

    amap = get_amap()
    try:
        return await amap.search_nearby(
            lng=lng,
            lat=lat,
            category=category,
            radius=radius,
        )
    except Exception as e:
        logger.warning(
            f"Amap API search_nearby failed for lng={lng}, lat={lat}: {e}. "
            "Falling back to local database."
        )
        # Nearby search fallback: return empty (no city context for DB query)
        return []


async def _fallback_db_search(
    city: str,
    category: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    """Fallback POI search using local database.

    Args:
        city: City name.
        category: Optional category filter.
        keyword: Optional keyword search.

    Returns:
        List of POI dicts matching the local DB format.
    """
    try:
        from sqlalchemy import select
        from geoalchemy2.shape import to_shape

        from app.database import async_session_factory
        from app.models.poi import POI

        async with async_session_factory() as session:
            stmt = select(POI).where(POI.city == city)

            if category:
                stmt = stmt.where(POI.category == category)

            if keyword:
                pattern = f"%{keyword}%"
                stmt = stmt.where(
                    POI.name.ilike(pattern) | POI.description.ilike(pattern)
                )

            stmt = stmt.limit(20)
            result = await session.execute(stmt)
            poi_rows = result.scalars().all()

            fallback_results: list[dict[str, Any]] = []
            for poi in poi_rows:
                lng, lat = 0.0, 0.0
                if poi.location is not None:
                    point = to_shape(poi.location)
                    lng, lat = point.x, point.y

                fallback_results.append(
                    {
                        "amap_id": str(poi.id),
                        "name": poi.name,
                        "address": poi.description or "",
                        "lng": lng,
                        "lat": lat,
                        "type": poi.category,
                        "city": poi.city,
                    }
                )

            logger.info(
                f"DB fallback returned {len(fallback_results)} POIs for city={city}"
            )
            return fallback_results

    except Exception as db_err:
        logger.error(f"DB fallback also failed: {db_err}")
        return []
