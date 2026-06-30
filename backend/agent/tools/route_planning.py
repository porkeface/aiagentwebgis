"""Route planning tool — wrapped for LangChain ReAct agent."""

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
) -> dict[str, Any]:
    """查询两点之间的驾车距离和时间。

    用于验证两个 POI 之间的实际路程，帮助判断是否适合安排在同一天。
    返回距离（公里）和预计时间（分钟）。

    驾车距离超过 20km 的两个 POI 通常不适合安排在同一天。

    Args:
        origin_lng: 起点经度
        origin_lat: 起点纬度
        dest_lng: 终点经度
        dest_lat: 终点纬度
        mode: 出行方式 — "driving"(驾车)、"walking"(步行)、"bicycling"(骑行)、"transit"(公交)
    """
    from agent.tools import get_amap

    amap = get_amap()
    return await amap.plan_route(
        origin=(origin_lng, origin_lat),
        destination=(dest_lng, dest_lat),
        mode=mode,
    )
