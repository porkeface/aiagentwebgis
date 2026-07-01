"""optimize_route tool — multi-start NN + 2-opt TSP with Amap distance matrix.

For N ≤ 8, builds a full real-road distance matrix via concurrent Amap
calls, then solves TSP with 2-opt improvement.  For larger N, falls back
to haversine-based ordering (multi-start NN + 2-opt) because the pairwise
matrix would exceed the free-tier QPS budget (~19s for 56 calls).

After ordering, a single ``plan_route_with_waypoints`` call fetches the
real driving polyline, segments, distance, and duration from Amap.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Max POIs for which we build a full Amap distance matrix.  Above this
# number haversine is used for ordering (still followed by a single Amap
# waypoint call for polyline data).
FULL_MATRIX_MAX_N = 8

# Max concurrent Amap calls during matrix build (≤ QPS limit, 3 for free tier).
MATRIX_CONCURRENCY = 3


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@tool
async def optimize_route(
    pois: list[dict[str, Any]],
    start_lng: float | None = None,
    start_lat: float | None = None,
    mode: str = "driving",
) -> dict[str, Any]:
    """优化多 POI 的最优驾车访问顺序（真实道路 TSP + 高德 route polyline）。

    对 N ≤ 8 的 POI 集合，先并发调用高德 API 构建真实道路距离矩阵，
    再用 2-opt 算法在真实矩阵上求出最优访问顺序，最后调用高德 waypoint
    API 获取完整 polyline、段间距离和时间。

    对 N > 8，用 haversine 多起点最近邻 + 2-opt 近似排序 + waypoint API。

    Args:
        pois: POI 列表，每个至少包含 name、lng、lat。
        start_lng: 可选起点经度。
        start_lat: 可选起点纬度。
        mode: 出行方式（"driving"/"walking"/"bicycling"/"transit"），
              途经点仅驾车模式支持。

    Returns:
        dict with:
        - ordered_pois: 最优访问顺序列表
        - segments: 段间 {from, to, distance_km, duration_min, polyline}
        - total_distance_km: 总驾车距离
        - total_duration_min: 总驾车时间
        - polyline: 完整路线坐标串（前端渲染用）
        - mode: 出行方式
        - matrix_source: "amap" | "haversine"
    """
    from agent.tools import get_amap
    from agent.tools.tsp_solver import solve_tsp
    from agent.tools.distance_matrix import build_distance_matrix

    if not pois:
        return {
            "ordered_pois": [], "segments": [], "total_distance_km": 0.0,
            "total_duration_min": 0.0, "polyline": "", "mode": mode,
            "matrix_source": "haversine",
        }

    amap = get_amap()
    work_pois = list(pois)  # don't mutate caller's list

    # If a start point is given, prepend it as a virtual POI
    if start_lng is not None and start_lat is not None:
        start_poi: dict[str, Any] = {"name": "起点", "lng": start_lng, "lat": start_lat}
        work_pois.insert(0, start_poi)

    n = len(work_pois)
    if n == 1:
        p = work_pois[0]
        return {
            "ordered_pois": [{"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}],
            "segments": [], "total_distance_km": 0.0, "total_duration_min": 0.0,
            "polyline": "", "mode": mode, "matrix_source": "single",
        }

    # ── Phase 1: TSP ordering ──────────────────────────────────────────
    dist_matrix: list[list[float]] | None = None
    matrix_source = "haversine"

    if n <= FULL_MATRIX_MAX_N:
        try:
            dist_km, _ = await build_distance_matrix(amap, work_pois, max_concurrent=MATRIX_CONCURRENCY)
            dist_matrix = dist_km
            matrix_source = "amap"
            logger.info("Built Amap distance matrix for %d POIs", n)
        except Exception:
            logger.warning("Amap distance matrix failed, falling back to haversine", exc_info=True)

    order, _ = solve_tsp(work_pois, dist_matrix)
    ordered = [work_pois[i] for i in order]

    # If we added a virtual start, remove it from the ordered list
    if start_lng is not None and start_lat is not None:
        # Remove the virtual start POI; the TSP already decided where to begin
        ordered = [p for p in ordered if p.get("name") != "起点"]
        if not ordered:
            ordered = [work_pois[0]]

    # ── Phase 2: Amap waypoint API for polyline ─────────────────────────
    if len(ordered) >= 2:
        try:
            origin = (ordered[0]["lng"], ordered[0]["lat"])
            destination = (ordered[-1]["lng"], ordered[-1]["lat"])
            waypoints = None
            if len(ordered) > 2 and mode == "driving":
                waypoints = [(p["lng"], p["lat"]) for p in ordered[1:-1]]

            result = await amap.plan_route_with_waypoints(
                origin=origin, destination=destination, waypoints=waypoints, mode=mode,
            )
            return _build_output(ordered, result, mode, matrix_source)

        except Exception:
            logger.exception("Waypoint API failed, using haversine segments")

    # ── Phase 3: Haversine fallback ─────────────────────────────────────
    return _haversine_output(ordered, mode, matrix_source)


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------


def _build_output(
    ordered: list[dict[str, Any]],
    amap_result: dict[str, Any],
    mode: str,
    matrix_source: str,
) -> dict[str, Any]:
    """Build tool output from an Amap waypoint result."""
    segments_raw: list[dict[str, Any]] = amap_result.get("segments", [])
    polyline_full = amap_result.get("polyline", "")

    # Split the full polyline per-segment for the frontend
    polyline_parts = polyline_full.split(";") if polyline_full else []

    segments: list[dict[str, Any]] = []
    cursor = 0
    for i in range(len(ordered) - 1):
        seg = segments_raw[i] if i < len(segments_raw) else {}
        seg_poly = ""
        # The Amap polyline is the concatenation of all step polylines;
        # each segment's polyline is roughly proportional to its step count.
        # We approximate by taking a slice of the full polyline.
        seg_len = len(polyline_parts)
        seg_count = max(1, seg_len // max(len(ordered) - 1, 1))
        end_cursor = min(cursor + seg_count * 3, seg_len)
        if cursor < seg_len:
            seg_poly = ";".join(polyline_parts[cursor:end_cursor])
        cursor = end_cursor

        segments.append({
            "from": ordered[i].get("name", "?"),
            "to": ordered[i + 1].get("name", "?"),
            "distance_km": seg.get("distance_km", 0),
            "duration_min": seg.get("duration_min", 0),
            "polyline": seg_poly,
            "mode": mode,
        })

    return {
        "ordered_pois": [
            {"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}
            for p in ordered
        ],
        "segments": segments,
        "total_distance_km": amap_result.get("distance_km", 0),
        "total_duration_min": amap_result.get("duration_min", 0),
        "polyline": polyline_full,
        "mode": mode,
        "matrix_source": matrix_source,
    }


def _haversine_output(
    ordered: list[dict[str, Any]],
    mode: str,
    matrix_source: str,
) -> dict[str, Any]:
    """Build tool output with haversine-estimated segments."""
    from agent.tools.tsp_solver import _haversine_km

    segments: list[dict[str, Any]] = []
    total = 0.0
    for i in range(len(ordered) - 1):
        d = _haversine_km(
            ordered[i].get("lng", 0), ordered[i].get("lat", 0),
            ordered[i + 1].get("lng", 0), ordered[i + 1].get("lat", 0),
        )
        segments.append({
            "from": ordered[i].get("name", "?"),
            "to": ordered[i + 1].get("name", "?"),
            "distance_km": round(d, 2),
            "duration_min": round(d * 3),  # rough 20km/h urban
            "polyline": "",
            "mode": mode,
        })
        total += d

    return {
        "ordered_pois": [
            {"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}
            for p in ordered
        ],
        "segments": segments,
        "total_distance_km": round(total, 2),
        "total_duration_min": round(total * 3),
        "polyline": "",
        "mode": mode,
        "matrix_source": matrix_source,
    }
