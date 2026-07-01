"""Distance matrix builder — concurrent Amap pairwise route calls.

Builds an N×N matrix of real driving distances/durations by calling
Amap's ``plan_route`` for every ordered pair (i, j) of POIs.  Uses an
asyncio semaphore to stay within the API QPS limit.

Typical usage (inside a tool):
    amap = get_amap()
    dist_km, dur_min = await build_distance_matrix(amap, pois)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default concurrency — matched to personal-tier QPS (3).  Can be raised
# for enterprise keys (30 QPS).
DEFAULT_MAX_CONCURRENT = 3


async def build_distance_matrix(
    amap: Any,
    pois: list[dict[str, Any]],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> tuple[list[list[float]], list[list[float]]]:
    """Build N×N distance and duration matrices via concurrent Amap calls.

    Args:
        amap: ``AmapService`` singleton from ``get_amap()``.
        pois: POI list, each must have ``lng`` and ``lat``.
        max_concurrent: Max in-flight Amap requests (default 3 ≈ 3 QPS).

    Returns:
        ``(dist_km, dur_min)`` — two N×N matrices.  ``dist_km[i][j]`` is
        the driving distance from POI i → POI j in km; ``dur_min`` is the
        estimated duration in minutes.  Diagonal entries are 0.0.
    """
    n = len(pois)
    if n <= 1:
        return ([[0.0]], [[0.0]])

    dist_km = [[0.0] * n for _ in range(n)]
    dur_min = [[0.0] * n for _ in range(n)]
    sem = asyncio.Semaphore(max_concurrent)
    failed: int = 0

    async def _one_pair(i: int, j: int) -> tuple[int, int, float, float]:
        nonlocal failed
        try:
            async with sem:
                result = await amap.plan_route(
                    origin=(pois[i]["lng"], pois[i]["lat"]),
                    destination=(pois[j]["lng"], pois[j]["lat"]),
                    mode="driving",
                )
            return (i, j, result.get("distance_km", 0.0), result.get("duration_min", 0.0))
        except Exception:
            logger.warning("Matrix pair (%d→%d) failed, using haversine fallback", i, j, exc_info=True)
            failed += 1
            d = _haversine_km(
                pois[i].get("lng", 0), pois[i].get("lat", 0),
                pois[j].get("lng", 0), pois[j].get("lat", 0),
            )
            return (i, j, d, d * 3)  # rough urban speed ~20 km/h → 3 min/km

    tasks = [_one_pair(i, j) for i in range(n) for j in range(n) if i != j]
    completed = 0

    for coro in asyncio.as_completed(tasks):
        i, j, d_km, d_min = await coro
        dist_km[i][j] = round(d_km, 2)
        dur_min[i][j] = round(d_min, 2)
        completed += 1

    if failed:
        logger.warning("Distance matrix: %d/%d pairs used haversine fallback", failed, completed)

    return (dist_km, dur_min)


# ---------------------------------------------------------------------------
# Local fallback
# ---------------------------------------------------------------------------

import math


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
