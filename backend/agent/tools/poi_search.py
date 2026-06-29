"""POI search tool functions — wraps AmapService.search_pois / place-around."""

from __future__ import annotations

from typing import Any


async def search_pois_tool(
    city: str,
    category: str,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    """Search POIs by city, category, and optional keyword.

    Args:
        city: City name, e.g. "北京".
        category: POI type category, e.g. "景点".
        keyword: Optional search keyword, e.g. "故宫".

    Returns:
        List of POI dicts from AmapService.
    """
    from agent.tools import get_amap

    amap = get_amap()
    return await amap.search_pois(city=city, category=category, keyword=keyword)


async def search_nearby_tool(
    lng: float,
    lat: float,
    category: str,
    radius: int = 1000,
) -> list[dict[str, Any]]:
    """Search nearby POIs around a coordinate.

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
    return await amap.search_nearby(
        lng=lng,
        lat=lat,
        category=category,
        radius=radius,
    )
