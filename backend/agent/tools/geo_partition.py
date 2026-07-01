"""geo_partition tool — cluster POIs by geographic proximity for day assignment.

Wraps recommendation.clustering.cluster_pois_for_days as a LangChain tool
so the agent can partition a pool of candidate POIs into daily zones.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def geo_partition(
    pois: list[dict[str, Any]],
    n_days: int,
    center_lng: float | None = None,
    center_lat: float | None = None,
) -> list[dict[str, Any]]:
    """按地理位置将 POI 分成 n_days 个区域，同区域 POI 地理位置邻近。

    使用 DBSCAN 密度聚类算法将候选 POI 按地理坐标分组。
    返回每天建议的 POI 子集，同一区域的 POI 应安排在同一天，
    避免跨区穿梭。

    在规划多日行程时，必须最先调用这个工具获取每日的 POI 分区。

    Args:
        pois: 候选 POI 列表，每个必须有 lng、lat、name、id 字段
        n_days: 旅行天数
        center_lng: 城市中心经度，用于排序分区（最近区域=第1天）
        center_lat: 城市中心纬度
    """
    from recommendation.clustering import cluster_pois_for_days

    if not pois:
        return [{"day": d, "zone": f"第{d}天", "pois": []} for d in range(1, n_days + 1)]

    if n_days <= 0:
        return []

    try:
        clusters = cluster_pois_for_days(
            pois=pois,
            n_days=n_days,
            center_lng=center_lng,
            center_lat=center_lat,
        )
    except Exception:
        logger.exception("geo_partition clustering failed")
        return [{"day": d, "zone": f"第{d}天", "pois": list(pois)} for d in range(1, n_days + 1)]

    # Add zone label for readability
    result: list[dict[str, Any]] = []
    for cluster in clusters:
        day_pois = cluster.get("pois", [])
        # Guess zone from the first POI's address or use day number
        zone = f"区域{cluster['day']}"
        if day_pois:
            addr = day_pois[0].get("address", "")
            if addr and isinstance(addr, str) and len(addr) > 2:
                # Extract district-like portion from address (first 2-4 chars after city)
                zone = addr[:6] if len(addr) >= 6 else addr
        result.append({
            "day": cluster["day"],
            "zone": zone,
            "pois": [
                {"id": p.get("id"), "name": p.get("name"), "lng": p.get("lng"), "lat": p.get("lat")}
                for p in day_pois
            ],
        })

    return result
