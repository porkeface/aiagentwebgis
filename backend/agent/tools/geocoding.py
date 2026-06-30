"""Geocoding tool functions — wraps AmapService.geocode / reverse_geocode."""

from __future__ import annotations

from typing import Any


async def geocode_tool(
    address: str,
    city: str | None = None,
) -> tuple[float, float]:
    """Geocode an address to (longitude, latitude).

    Args:
        address: Address string, e.g. "北京市东城区景山前街4号".
        city: Optional city hint for disambiguation.

    Returns:
        Tuple of (longitude, latitude).
    """
    from agent.tools import get_amap

    amap = get_amap()
    # Prepend city to address if provided, for better disambiguation
    full_address = f"{city}{address}" if city else address
    return await amap.geocode(full_address)


async def reverse_geocode_tool(
    lng: float,
    lat: float,
) -> dict[str, str]:
    """Reverse geocode coordinates to an address.

    Args:
        lng: Longitude.
        lat: Latitude.

    Returns:
        Dict with keys: address, city.
    """
    from agent.tools import get_amap

    amap = get_amap()
    return await amap.reverse_geocode(lng, lat)
