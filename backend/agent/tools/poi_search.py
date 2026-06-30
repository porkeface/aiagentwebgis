"""POI search tool functions — wraps AmapService.search_pois / place-around.

Pure Amap API calls — no local database fallback.
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

    Tries Amap API first. On failure returns an empty list with a warning
    log (no local fallback — seed data has been removed).

    Args:
        city: City name, e.g. "北京".
        category: POI type category, e.g. "景点".
        keyword: Optional search keyword, e.g. "故宫".

    Returns:
        List of POI dicts from AmapService. Empty list if API fails.
    """
    from agent.tools import get_amap

    amap = get_amap()
    try:
        return await amap.search_pois(city=city, category=category, keyword=keyword)
    except Exception as e:
        logger.warning(
            f"Amap API search_pois failed for city={city}, category={category}: {e}. "
            "No local fallback available (seed data removed). Returning empty list."
        )
        return []


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
            "Returning empty list."
        )
        # Nearby search fallback: return empty (no city context for DB query)
        return []
