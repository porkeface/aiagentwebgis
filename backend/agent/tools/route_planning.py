"""Route planning tool function — wraps AmapService.plan_route."""

from __future__ import annotations

from typing import Any


async def plan_route_tool(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
    mode: str = "driving",
) -> dict[str, Any]:
    """Plan a route between two coordinate pairs.

    Args:
        origin_lng: Origin longitude.
        origin_lat: Origin latitude.
        dest_lng: Destination longitude.
        dest_lat: Destination latitude.
        mode: Travel mode — "driving", "walking", "bicycling", or "transit".

    Returns:
        Dict with keys: distance_km, duration_min, polyline.
    """
    from agent.tools import get_amap

    amap = get_amap()
    return await amap.plan_route(
        origin=(origin_lng, origin_lat),
        destination=(dest_lng, dest_lat),
        mode=mode,
    )
