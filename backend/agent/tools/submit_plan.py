"""submit_plan tool — validates and submits daily trip plans.

The LLM calls this after completing its trip layout.  The tool validates
the plan structure and basic rules (no duplicate POIs, reasonable daily
time budget) then returns the validated plan.  The API stream handler
intercepts the tool output and emits the ``route_result`` SSE event.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import tool

from app.services.duration_estimator import estimate_poi_duration_from_dict, estimate_daily_capacity


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_MAX_DAILY_BUDGET_MIN = 840  # 14 hours — hard upper bound
_TRANSIT_RATIO_WARN = 1.5     # warn when transit > 1.5× visit time

# Business rules — hard coded, not LLM-dependent
MIN_POI_RATING = 3.5           # minimum acceptable rating
MAX_POI_SPREAD_KM = 35         # max geographic spread within one day


def _validate_plan(plan_data: dict[str, Any]) -> list[str]:
    """Validate a submitted trip plan.  Returns a list of issues (empty = clean).

    Enforces structural correctness AND business rules (POI count, rating,
    geographic clustering).  The agent is no longer solely trusted.
    """
    import math

    issues: list[str] = []

    # ── Structural checks ────────────────────────────────────────────────
    city = plan_data.get("city", "")
    if not city:
        issues.append("city 不能为空")

    days = plan_data.get("days", 0)
    if not isinstance(days, int) or days < 1 or days > 30:
        issues.append("days 必须是 1-30 的整数")

    daily_plans = plan_data.get("daily_plans", [])
    if not isinstance(daily_plans, list) or not daily_plans:
        issues.append("daily_plans 不能为空")
        return issues

    seen_poi_ids: set[str] = set()

    for day_plan in daily_plans:
        day_num = day_plan.get("day", 0)
        if not isinstance(day_num, int) or day_num < 1:
            issues.append(f"daily_plans[?].day 无效: {day_num}")
            continue

        pois = day_plan.get("pois", [])
        if not isinstance(pois, list) or len(pois) < 1:
            issues.append(f"第{day_num}天: 至少需要 1 个 POI")
            continue

        # ── Dynamic capacity check per day ──
        durations = [
            p.get("visit_duration_min") or estimate_poi_duration_from_dict(p)
            for p in pois
        ]
        dynamic_cap = estimate_daily_capacity(durations)
        if len(pois) > dynamic_cap + 1:  # +1 tolerance
            issues.append(
                f"第{day_num}天: 景点数量({len(pois)})超过动态容量({dynamic_cap})，"
                f"建议将部分景点拆分到其他天"
            )

        # ── Duplicate & coordinate check ──
        for i, poi in enumerate(pois):
            poi_id = str(poi.get("poi_id", ""))
            if not poi_id:
                issues.append(f"第{day_num}天, POI[{i}]: 缺少 poi_id")
                continue
            if poi_id in seen_poi_ids:
                issues.append(f"POI '{poi_id}' 在多个天中出现，每个 POI 只能安排一次")
            seen_poi_ids.add(poi_id)

            # Coord validation: each POI must carry real coordinates
            lng = poi.get("lng")
            lat = poi.get("lat")
            if not isinstance(lng, (int, float)) or not isinstance(lat, (int, float)):
                issues.append(
                    f"第{day_num}天, POI[{i}] '{poi.get('name', poi_id)}': "
                    f"缺 lng/lat 坐标，必须填写真实经纬度"
                )
                continue
            if not (-180 <= float(lng) <= 180 and -90 <= float(lat) <= 90):
                issues.append(f"第{day_num}天, POI[{i}]: 坐标 lng={lng}, lat={lat} 超出合法范围")

            # ── Business rule: minimum rating ──
            rating = poi.get("rating")
            if isinstance(rating, (int, float)) and rating > 0 and rating < MIN_POI_RATING:
                issues.append(
                    f"第{day_num}天: '{poi.get('name', poi_id)}' 评分({rating})低于"
                    f"最低标准({MIN_POI_RATING})，建议替换为更高评分景点"
                )

        # ── Business rule: geographic spread ──
        if len(pois) >= 3:
            valid_coords = [
                (float(p["lng"]), float(p["lat"]))
                for p in pois
                if isinstance(p.get("lng"), (int, float))
                and isinstance(p.get("lat"), (int, float))
            ]
            if len(valid_coords) >= 3:
                centroid_lng = sum(c[0] for c in valid_coords) / len(valid_coords)
                centroid_lat = sum(c[1] for c in valid_coords) / len(valid_coords)
                max_dist = 0.0
                for clng, clat in valid_coords:
                    dlat = math.radians(clat - centroid_lat)
                    dlng = math.radians(clng - centroid_lng)
                    a = (
                        math.sin(dlat / 2) ** 2
                        + math.cos(math.radians(centroid_lat))
                        * math.cos(math.radians(clat))
                        * math.sin(dlng / 2) ** 2
                    )
                    d = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    if d > max_dist:
                        max_dist = d
                if max_dist > MAX_POI_SPREAD_KM:
                    issues.append(
                        f"第{day_num}天: POI 地理分布过散"
                        f"（最远点距中心 {max_dist:.0f}km > {MAX_POI_SPREAD_KM}km），"
                        f"建议将距离较远的景点移到其他天"
                    )

        # ── Time budget (hard cap) ──
        total_dur = day_plan.get("total_duration_min", 0) or 0
        if isinstance(total_dur, (int, float)) and total_dur > _MAX_DAILY_BUDGET_MIN:
            issues.append(
                f"第{day_num}天: 总时长 {total_dur:.0f}min 超过日上限 "
                f"{_MAX_DAILY_BUDGET_MIN}min，请将该天 POI 拆分到多天"
            )

        # ── Transit ratio warning (soft) ──
        total_visit = sum(
            p.get("visit_duration_min", 0) or 0
            for p in pois
            if isinstance(p.get("visit_duration_min"), (int, float))
        )
        total_transit = day_plan.get("total_transit_min", 0) or 0
        if (
            isinstance(total_transit, (int, float))
            and total_transit > 0
            and total_visit > 0
            and total_transit > total_visit * _TRANSIT_RATIO_WARN
        ):
            issues.append(
                f"第{day_num}天: 交通时间({total_transit:.0f}min)远大于游览时间"
                f"({total_visit:.0f}min)，POI 可能过于分散"
            )

    return issues


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@tool
async def submit_plan(
    city: str,
    days: int,
    daily_plans: list[dict[str, Any]],
) -> dict[str, Any]:
    """提交并验证每日行程计划。

    提交后系统会**自动**对每天调用高德驾车路径规划，获取真实道路
    polyline、最优访问顺序、真实距离和时间。LLM 无需手动调用 plan_day_route。

    校验规则：
    - POI 不重复（同一 POI 只能出现一次）
    - 每天至少 1 个 POI
    - 每天总时长不超过 840 分钟（14 小时）
    - 交通时间占比合理（软性提醒）

    校验通过后，行程会被推送到地图上展示。

    Args:
        city: 城市名称，如 "北京"
        days: 旅行天数
        daily_plans: 每日计划列表，每项格式（每个 POI 必须包含 poi_id/name/lng/lat/visit_duration_min）：
            {
              "day": 1,
              "day_theme": "皇城中轴线漫游",
              "pois": [
                {"poi_id": "B001...", "name": "故宫", "lng": 116.397, "lat": 39.916, "visit_duration_min": 120},
                {"poi_id": "B002...", "name": "全聚德", "lng": 116.402, "lat": 39.913, "visit_duration_min": 60}
              ],
              "total_duration_min": 280,
              "total_transit_min": 35
            }
    """
    # ── Auto-route each day if not already routed ────────────────────────
    _sorted = sorted(daily_plans, key=lambda d: d.get("day", 0))
    _tasks = [
        route_one_day(dp) if not (dp.get("segments") or dp.get("polyline"))
        else asyncio.sleep(0, result=dp)
        for dp in _sorted
    ]
    enriched_plans = await asyncio.gather(*_tasks)

    plan = {"city": city, "days": days, "daily_plans": enriched_plans}
    issues = _validate_plan(plan)

    if issues:
        return {
            "status": "rejected",
            "errors": issues,
            "hint": (
                "请修正上述问题后重新调用 submit_plan。常见修正方法："
                "1) 删除跨天重复的 POI 并替换为新的；"
                "2) 总时长超限的天拆分为多天；"
                "3) 确保每个 POI 有真实的 poi_id/name/lng/lat。"
            ),
        }

    return {
        "status": "accepted",
        "city": city,
        "days": days,
        "daily_plans": enriched_plans,
    }


def _fallback_segments(pois: list[dict[str, Any]], dp: dict[str, Any]) -> None:
    """Compute haversine segments when Amap API is unavailable."""
    import math
    def _h(p1, p2):
        r = 6371.0
        dlat = math.radians(p2["lat"] - p1["lat"])
        dlng = math.radians(p2["lng"] - p1["lng"])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(p1["lat"])) * math.cos(math.radians(p2["lat"])) * math.sin(dlng/2)**2
        return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    segs = []
    total_d = 0.0
    for i in range(len(pois)-1):
        d = _h(pois[i], pois[i+1])
        segs.append({"distance_km": round(d,2), "duration_min": round(d*3)})
        total_d += d
    dp["total_distance_km"] = round(total_d, 2)
    dp["total_transit_min"] = round(total_d * 3)
    dp["polyline"] = ""
    dp["segments"] = segs


async def route_one_day(dp: dict[str, Any]) -> dict[str, Any]:
    """TSP sort a single day's POIs and fetch Amap waypoint route."""
    from agent.tools import get_amap
    from agent.tools.tsp_solver import solve_tsp

    pois = dp.get("pois", [])
    result: dict[str, Any] = {
        "day": dp.get("day"),
        "day_theme": dp.get("day_theme"),
        "total_duration_min": dp.get("total_duration_min", 0),
        "total_transit_min": dp.get("total_transit_min", 0),
    }
    if len(pois) >= 2:
        try:
            order, _ = solve_tsp(pois)
            ordered = [pois[i] for i in order]
        except Exception:
            ordered = pois
        result["pois"] = ordered
        try:
            amap = get_amap()
            origin = (ordered[0]["lng"], ordered[0]["lat"])
            destination = (ordered[-1]["lng"], ordered[-1]["lat"])
            wps = None
            if len(ordered) > 2:
                wps = [(p["lng"], p["lat"]) for p in ordered[1:-1]]
            route = await amap.plan_route_with_waypoints(
                origin=origin, destination=destination, waypoints=wps, mode="driving",
            )
            result["total_distance_km"] = route.get("distance_km", 0)
            result["total_transit_min"] = route.get("duration_min", 0)
            result["polyline"] = route.get("polyline", "")
            result["segments"] = route.get("segments", [])
        except Exception:
            _fallback_segments(ordered, result)
    else:
        result["pois"] = list(pois)
    return result
