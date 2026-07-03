"""plan_day_route tool — single-day optimal driving route via Amap waypoints.

Calls Amap's multi-waypoint driving direction API to produce a real-world
route for a day's POIs. The TSP ordering is handled internally by Amap's
optimized_order parameter, so this tool does not depend on the (now removed)
optimize_route helper.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from agent.tools.tsp_solver import _haversine_km

logger = logging.getLogger(__name__)


def _order_pois_tsp(pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order a small list of POIs via the shared TSP solver.

    Returns a new list in optimal visit order.  Pure function — no I/O.
    """
    from agent.tools.tsp_solver import solve_tsp

    n = len(pois)
    if n <= 1:
        return list(pois)
    order, _ = solve_tsp(pois)
    return [pois[i] for i in order]


@tool
async def plan_day_route(
    pois: list[dict[str, Any]],
    mode: str = "driving",
    optimized_order: list[int] | None = None,
) -> dict[str, Any]:
    """计算单日多 POI 的最优驾车访问路线。

    给定一天内的 POI 列表，自动用 TSP 算法排序后用高德驾车路径规划 API
    获取真实道路距离、预计时间和路线 polyline。

    返回：
    - ordered_pois: 最优访问顺序
    - total_distance_km: 总驾车距离
    - total_duration_min: 总驾车时间
    - polyline: 完整路线坐标串（用于前端渲染）
    - segments: 每段 {distance_km, duration_min, polyline, mode} 明细
    - mode: 出行方式

    Args:
        pois: 当天的 POI 列表，每个必须有 lng、lat、name。建议 2-10 个。
        mode: 出行方式 — "driving"（驾车）、"walking"（步行）、
              "bicycling"（骑行）、"transit"（公交）。
              注意：途经点功能仅驾车模式支持。
        optimized_order: 可选的预排序索引列表。传入时跳过内部 TSP 排序，
              直接按给定顺序调用高德 API。用于全局排序后的子集路线规划。
    """
    from agent.tools import get_amap

    if not pois:
        return {
            "ordered_pois": [], "total_distance_km": 0, "total_duration_min": 0,
            "polyline": "", "segments": [], "mode": mode,
        }

    if optimized_order is not None:
        ordered = [pois[i] for i in optimized_order if 0 <= i < len(pois)]
    else:
        ordered = _order_pois_tsp(pois)

    if len(ordered) == 1:
        p = ordered[0]
        return {
            "ordered_pois": [{"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}],
            "total_distance_km": 0, "total_duration_min": 0,
            "polyline": "", "segments": [], "mode": mode,
        }

    amap = get_amap()
    origin = (ordered[0]["lng"], ordered[0]["lat"])
    destination = (ordered[-1]["lng"], ordered[-1]["lat"])

    waypoints: list[tuple[float, float]] | None = None
    if len(ordered) > 2:
        waypoints = [(p["lng"], p["lat"]) for p in ordered[1:-1]]

    try:
        result = await amap.plan_route_with_waypoints(
            origin=origin, destination=destination, waypoints=waypoints, mode=mode,
        )
        result["mode"] = mode
        return {
            "ordered_pois": [
                {"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}
                for p in ordered
            ],
            **result,
        }
    except Exception:
        logger.exception("plan_day_route failed for %d POIs", len(pois))

        total = 0.0
        segments: list[dict[str, Any]] = []
        for i in range(len(ordered) - 1):
            d = _haversine_km(ordered[i], ordered[i + 1])
            segments.append({
                "from": ordered[i].get("name", "?"),
                "to": ordered[i + 1].get("name", "?"),
                "distance_km": round(d, 2),
                "duration_min": round(d * 3),
                "polyline": "",
                "mode": mode,
            })
            total += d
        return {
            "ordered_pois": [
                {"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}
                for p in ordered
            ],
            "total_distance_km": round(total, 2),
            "total_duration_min": round(total * 3),
            "polyline": "",
            "segments": segments,
            "mode": mode,
        }
