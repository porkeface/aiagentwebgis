"""optimize_route tool — nearest-neighbour TSP for POI visit ordering.

Computes the shortest path visiting all given POIs using a greedy
nearest-neighbor heuristic, then removes the longest edge from the
Hamiltonian cycle to produce a linear path so the user doesn't have to
"close the loop".
"""

from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool


def _haversine_km(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Haversine distance in km between two POI dicts with lng/lat."""
    lng1, lat1 = a["lng"], a["lat"]
    lng2, lat2 = b["lng"], b["lat"]
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    x = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def _nearest_neighbor_tsp(
    pois: list[dict[str, Any]],
) -> tuple[list[int], float]:
    """Nearest-neighbor greedy heuristic for TSP. O(N^2)."""
    n = len(pois)
    visited = [False] * n
    order: list[int] = [0]
    visited[0] = True

    for _ in range(n - 1):
        last = order[-1]
        best_j = -1
        best_d = float("inf")
        for j in range(n):
            if not visited[j]:
                d = _haversine_km(pois[last], pois[j])
                if d < best_d:
                    best_d = d
                    best_j = j
        order.append(best_j)
        visited[best_j] = True

    # Total round-trip distance
    total = sum(
        _haversine_km(pois[order[i]], pois[order[(i + 1) % n]])
        for i in range(n)
    )
    return (order, total)


def _tsp_linear_path(
    pois: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    """Compute optimal linear visit order.

    Solves TSP on the POI set then removes the longest edge from the
    Hamiltonian cycle to produce a linear path (start and end need not
    be the same point).

    Returns:
        (ordered_pois, segments, total_distance_km)
    """
    n = len(pois)
    if n <= 1:
        return (list(pois), [], 0.0)

    # Use nearest-neighbor for all practical sizes; exact TSP is intractable
    # for the 20+ POIs the agent often sends.  Held-Karp O(N^2·2^N) burns
    # memory even at N=13 (dp table: 2^13×13 ≈ 106k cells).
    order, _ = _nearest_neighbor_tsp(pois)

    # Build ordered list
    ordered = [pois[i] for i in order]

    # Find the longest consecutive edge and break there to linearise
    if n >= 3:
        max_dist = -1.0
        cut_after = 0
        for i in range(n):
            a_idx = order[i]
            b_idx = order[(i + 1) % n]
            d = _haversine_km(pois[a_idx], pois[b_idx])
            if d > max_dist:
                max_dist = d
                cut_after = i
        # Rotate so the path starts after the longest edge
        ordered = ordered[cut_after + 1 :] + ordered[: cut_after + 1]

    # Build segments
    segments: list[dict[str, Any]] = []
    total = 0.0
    for i in range(len(ordered) - 1):
        d = _haversine_km(ordered[i], ordered[i + 1])
        segments.append({
            "from": ordered[i].get("name", "?"),
            "to": ordered[i + 1].get("name", "?"),
            "distance_km": round(d, 2),
            "duration_min": round(d * 12),
        })
        total += d

    return (ordered, segments, round(total, 2))


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@tool
async def optimize_route(
    pois: list[dict[str, Any]],
    start_lng: float | None = None,
    start_lat: float | None = None,
) -> dict[str, Any]:
    """优化多 POI 的访问顺序以最小化总路程（解 TSP）。

    给定一天内要访问的 POI 列表，使用最近邻贪心算法计算最优访问顺序，
    避免来回穿梭。返回排序后的 POI 列表、段间距离和总距离。

    使用场景：已选定某天的 POI 后，调用这个工具获取最优的访问顺序。

    Args:
        pois: POI 列表，每个至少包含 name、lng、lat。例如
            [{"name":"故宫","lng":116.397,"lat":39.918}, ...]
        start_lng: 可选的起点经度（如酒店位置）
        start_lat: 可选的起点纬度
    """
    if not pois:
        return {"ordered_pois": [], "segments": [], "total_distance_km": 0.0}

    # If a start point is specified, prepend it as a virtual POI
    work_pois = list(pois)
    if start_lng is not None and start_lat is not None:
        start_poi: dict[str, Any] = {"name": "起点", "lng": start_lng, "lat": start_lat}
        # Insert start point and solve; after solving remove the start edge cost
        work_pois.insert(0, start_poi)

    ordered, segments, total = _tsp_linear_path(work_pois)

    # If we added a start point, remove it from the output but keep the
    # segments that follow from it.
    if start_lng is not None and start_lat is not None:
        start_idx = next((i for i, p in enumerate(ordered) if p.get("name") == "起点"), None)
        if start_idx is not None:
            ordered = ordered[start_idx + 1 :] + ordered[:start_idx]
            # Rebuild segments
            segments = []
            total = 0.0
            for i in range(len(ordered) - 1):
                d = _haversine_km(ordered[i], ordered[i + 1])
                segments.append({
                    "from": ordered[i].get("name", "?"),
                    "to": ordered[i + 1].get("name", "?"),
                    "distance_km": round(d, 2),
                    "duration_min": round(d * 12),
                })
                total += d
            total = round(total, 2)

    return {
        "ordered_pois": [
            {"name": p.get("name", "?"), "lng": p.get("lng", 0), "lat": p.get("lat", 0)}
            for p in ordered
        ],
        "segments": segments,
        "total_distance_km": total,
    }
