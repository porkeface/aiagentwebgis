"""Route planning tool — wrapped for LangChain ReAct agent.

Supports both two-point routing and multi-waypoint driving routes.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
async def plan_route(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
    mode: str = "driving",
    waypoints: list[dict[str, float]] | None = None,
) -> dict[str, Any]:
    """查询两点之间的驾车距离和时间。支持途经点。

    用于验证两个 POI 之间的实际路程，或传入途经点获取完整的每日驾车路线。
    驾车距离超过 20km 的两个 POI 通常不适合安排在同一天。

    Args:
        origin_lng: 起点经度
        origin_lat: 起点纬度
        dest_lng: 终点经度
        dest_lat: 终点纬度
        mode: 出行方式 — "driving"(驾车)、"walking"(步行)、"bicycling"(骑行)、"transit"(公交)
        waypoints: 途经点列表 [{"lng":116.4,"lat":39.9}, ...]，仅驾车模式支持，最多 16 个
    """
    from agent.tools import get_amap

    amap = get_amap()

    wp_list: list[tuple[float, float]] | None = None
    if waypoints:
        wp_list = [(wp["lng"], wp["lat"]) for wp in waypoints]

    if wp_list and mode == "driving":
        return await amap.plan_route_with_waypoints(
            origin=(origin_lng, origin_lat),
            destination=(dest_lng, dest_lat),
            waypoints=wp_list,
            mode=mode,
        )

    return await amap.plan_route(
        origin=(origin_lng, origin_lat),
        destination=(dest_lng, dest_lat),
        mode=mode,
    )
