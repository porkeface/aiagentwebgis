"""TSP route optimization — nearest neighbor + 2-opt improvement.

Pure function, no I/O.  Uses haversine distance (R = 6371.0 km) to build a
distance matrix over daily POIs, applies a nearest-neighbour heuristic
(starting from the POI closest to the city center), then refines the tour
with the classic 2-opt local search until no improving swap exists.
"""

from __future__ import annotations

import copy
import math
from typing import Any

# Earth radius in kilometres (WGS-84 mean)
_R_KM = 6371.0


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in km between two lat/lng points (WGS-84).

    Args:
        lat1: Latitude of point 1 (degrees).
        lng1: Longitude of point 1 (degrees).
        lat2: Latitude of point 2 (degrees).
        lng2: Longitude of point 2 (degrees).

    Returns:
        Great-circle distance in kilometres.
    """
    lat1_r, lng1_r = math.radians(lat1), math.radians(lng1)
    lat2_r, lng2_r = math.radians(lat2), math.radians(lng2)

    dlat = lat2_r - lat1_r
    dlng = lng2_r - lng1_r

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2.0) ** 2
    )
    return 2.0 * _R_KM * math.asin(math.sqrt(a))


def _build_distance_matrix(pois: list[dict]) -> list[list[float]]:
    """Build an n×n symmetric haversine distance matrix."""
    n = len(pois)
    mat: list[list[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        lat_i, lng_i = pois[i]["lat"], pois[i]["lng"]
        for j in range(i + 1, n):
            d = haversine_km(lat_i, lng_i, pois[j]["lat"], pois[j]["lng"])
            mat[i][j] = d
            mat[j][i] = d
    return mat


def _tour_distance(order: list[int], dist: list[list[float]]) -> float:
    """Total path distance along *order* (open tour, no return to start)."""
    total = 0.0
    for k in range(len(order) - 1):
        total += dist[order[k]][order[k + 1]]
    return total


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------


def _nearest_neighbor(
    start_idx: int,
    dist: list[list[float]],
) -> list[int]:
    """Nearest-neighbour greedy tour starting from *start_idx*."""
    n = len(dist)
    visited = [False] * n
    order = [start_idx]
    visited[start_idx] = True

    for _ in range(n - 1):
        current = order[-1]
        best_dist = math.inf
        best_idx = -1
        for j in range(n):
            if not visited[j] and dist[current][j] < best_dist:
                best_dist = dist[current][j]
                best_idx = j
        order.append(best_idx)
        visited[best_idx] = True

    return order


def _two_opt(order: list[int], dist: list[list[float]]) -> list[int]:
    """2-opt local search until no improving reversal is found.

    For an open TSP the cost of the tour is the sum of consecutive edges.
    Reversing the segment [i+1 .. j] removes edges (i, i+1) and (j, j+1)
    and adds edges (i, j) and (i+1, j+1).  The move is improving when the
    new edges are shorter.
    """
    improved = True
    best = list(order)

    while improved:
        improved = False
        for i in range(len(best) - 2):
            for j in range(i + 2, len(best)):
                # Skip if j is the last node — removing edge (j, j+1) doesn't exist
                # in an open tour, so only consider j < len(best) - 1.
                if j == len(best) - 1:
                    continue

                d_before = dist[best[i]][best[i + 1]] + dist[best[j]][best[j + 1]]
                d_after = dist[best[i]][best[j]] + dist[best[i + 1]][best[j + 1]]

                if d_after < d_before - 1e-12:
                    best[i + 1 : j + 1] = reversed(best[i + 1 : j + 1])
                    improved = True

    return best


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def optimize_daily_route(
    pois: list[dict],
    center_lng: float | None = None,
    center_lat: float | None = None,
) -> dict[str, Any]:
    """Optimise the visiting order of POIs for a single day (open TSP).

    Algorithm:
    1. Build a haversine distance matrix.
    2. Pick the starting POI: closest to (*center_lng*, *center_lat*),
       or POI 0 if no centre is given.
    3. Construct an initial tour with nearest-neighbour.
    4. Improve with 2-opt local search.

    Args:
        pois: List of POI dicts, each with ``"lat"`` and ``"lng"`` keys.
              Optional ``"id"`` field used for segment references.
        center_lng: Optional city-centre longitude for choosing the start POI.
        center_lat: Optional city-centre latitude for choosing the start POI.

    Returns:
        ``{"ordered_pois": [...], "total_distance_km": float, "segments": [...]}``
        where each segment is ``{"from_poi_id": ..., "to_poi_id": ..., "distance_km": float}``.
    """
    if not pois:
        return {"ordered_pois": [], "total_distance_km": 0.0, "segments": []}

    # Work on copies so we never mutate input
    pois_copy = [copy.deepcopy(p) for p in pois]

    # ---- edge case: single POI ----
    if len(pois_copy) == 1:
        out_poi = pois_copy[0]
        out_poi["day_order"] = 1
        return {"ordered_pois": [out_poi], "total_distance_km": 0.0, "segments": []}

    # ---- distance matrix ----
    dist = _build_distance_matrix(pois_copy)

    # ---- choose starting POI ----
    if center_lng is not None and center_lat is not None:
        start_idx = min(
            range(len(pois_copy)),
            key=lambda i: haversine_km(
                pois_copy[i]["lat"],
                pois_copy[i]["lng"],
                center_lat,
                center_lng,
            ),
        )
    else:
        start_idx = 0

    # ---- nearest-neighbour initial tour ----
    nn_order = _nearest_neighbor(start_idx, dist)

    # ---- 2-opt improvement ----
    order = _two_opt(nn_order, dist)

    # ---- build result ----
    ordered_pois: list[dict] = []
    for rank, idx in enumerate(order, start=1):
        poi_out = pois_copy[idx]
        poi_out["day_order"] = rank
        ordered_pois.append(poi_out)

    segments: list[dict] = []
    for k in range(len(ordered_pois) - 1):
        src_idx = order[k]
        dst_idx = order[k + 1]
        segments.append(
            {
                "from_poi_id": pois_copy[src_idx].get("id"),
                "to_poi_id": pois_copy[dst_idx].get("id"),
                "distance_km": dist[src_idx][dst_idx],
            }
        )

    total = _tour_distance(order, dist)

    return {
        "ordered_pois": ordered_pois,
        "total_distance_km": total,
        "segments": segments,
    }
