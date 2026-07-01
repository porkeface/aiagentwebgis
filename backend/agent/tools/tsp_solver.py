"""TSP solver — multi-start nearest-neighbor + 2-opt improvement.

Pure functions, no I/O.  Can use either a pre-built real-road distance
matrix (from ``distance_matrix.py``) or fall back to haversine estimates.
"""

from __future__ import annotations

import math
from typing import Any


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _pair_dist(
    pois: list[dict[str, Any]],
    dist_matrix: list[list[float]] | None,
    i: int,
    j: int,
) -> float:
    """Distance between POI i and j — real if matrix given, else haversine."""
    if dist_matrix is not None:
        return dist_matrix[i][j]
    return _haversine_km(
        pois[i].get("lng", 0), pois[i].get("lat", 0),
        pois[j].get("lng", 0), pois[j].get("lat", 0),
    )


def _nn_from_start(
    pois: list[dict[str, Any]],
    dist_matrix: list[list[float]] | None,
    start: int,
) -> tuple[list[int], float]:
    """Nearest-neighbor greedy path from a given starting POI index."""
    n = len(pois)
    visited = [False] * n
    order = [start]
    visited[start] = True
    total = 0.0

    for _ in range(n - 1):
        last = order[-1]
        best_j = -1
        best_d = float("inf")
        for j in range(n):
            if not visited[j]:
                d = _pair_dist(pois, dist_matrix, last, j)
                if d < best_d:
                    best_d = d
                    best_j = j
        order.append(best_j)
        visited[best_j] = True
        total += best_d

    return (order, total)


def _swap_gain(
    pois: list[dict[str, Any]],
    dist_matrix: list[list[float]] | None,
    order: list[int],
    i: int,
    j: int,
) -> float:
    """Net distance change if we reverse the segment order[i:j+1].

    Positive = worse, negative = improvement.
    """
    n = len(order)
    a = order[i - 1] if i > 0 else order[i]        # virtual self-edge if at start
    b = order[i]
    c = order[j]
    d = order[j + 1] if j + 1 < n else order[j]    # virtual self-edge if at end

    old_dist = _pair_dist(pois, dist_matrix, a, b) + _pair_dist(pois, dist_matrix, c, d)
    new_dist = _pair_dist(pois, dist_matrix, a, c) + _pair_dist(pois, dist_matrix, b, d)
    return new_dist - old_dist


def _path_total(
    pois: list[dict[str, Any]],
    dist_matrix: list[list[float]] | None,
    order: list[int],
) -> float:
    """Total distance of a linear path through the given order."""
    total = 0.0
    for k in range(len(order) - 1):
        total += _pair_dist(pois, dist_matrix, order[k], order[k + 1])
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def solve_tsp(
    pois: list[dict[str, Any]],
    dist_matrix: list[list[float]] | None = None,
) -> tuple[list[int], float]:
    """Find the best linear visit order for a set of POIs.

    Algorithm: multi-start nearest-neighbor (every POI as starting point)
    followed by 2-opt swap improvement.

    Args:
        pois: POI list with ``lng``/``lat`` fields.
        dist_matrix: Optional N×N real-road distance matrix (km).  When
            omitted, haversine straight-line distances are used instead.

    Returns:
        ``(order_indices, total_distance_km)`` — ``order_indices`` is a
        permutation of ``range(len(pois))`` giving the optimal visit order.
        Does NOT form a cycle (start ≠ end).
    """
    n = len(pois)
    if n <= 1:
        return ([0] if n == 1 else [], 0.0)
    if n == 2:
        return ([0, 1], _pair_dist(pois, dist_matrix, 0, 1))

    # Phase 1: multi-start NN
    best_order: list[int] | None = None
    best_total = float("inf")
    for start in range(n):
        order, total = _nn_from_start(pois, dist_matrix, start)
        if total < best_total:
            best_order = order
            best_total = total

    # Phase 2: 2-opt swap improvement
    improved = True
    iterations = 0
    max_iterations = n * 10  # safety limit
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        for i in range(1, n - 1):
            for j in range(i + 1, min(n - 1, i + 5)):  # local window
                gain = _swap_gain(pois, dist_matrix, best_order, i, j)
                if gain < -0.01:
                    best_order[i : j + 1] = reversed(best_order[i : j + 1])
                    best_total += gain
                    improved = True
        # Also try wider window every few iterations
        if iterations % 3 == 0:
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    gain = _swap_gain(pois, dist_matrix, best_order, i, j)
                    if gain < -0.01:
                        best_order[i : j + 1] = reversed(best_order[i : j + 1])
                        best_total += gain
                        improved = True

    return (best_order, round(best_total, 2))
