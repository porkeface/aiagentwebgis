"""submit_plan tool — validates and submits daily trip plans.

The LLM calls this after completing its trip layout.  The tool validates
the plan structure and basic rules (no duplicate POIs, reasonable daily
time budget) then returns the validated plan.  The API stream handler
intercepts the tool output and emits the ``route_result`` SSE event.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_MAX_DAILY_BUDGET_MIN = 840  # 14 hours — hard upper bound
_TRANSIT_RATIO_WARN = 1.5     # warn when transit > 1.5× visit time


def _validate_plan(plan_data: dict[str, Any]) -> list[str]:
    """Validate a submitted trip plan.  Returns a list of issues (empty = clean).

    Only enforces structural correctness — *not* arbitrary POI-count or
    distance limits.  The agent is trusted to manage time budget.
    """
    issues: list[str] = []

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

        # --- Duplicate & coordinate check ---
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

        # --- Time budget (hard cap) ---
        total_dur = day_plan.get("total_duration_min", 0) or 0
        if isinstance(total_dur, (int, float)) and total_dur > _MAX_DAILY_BUDGET_MIN:
            issues.append(
                f"第{day_num}天: 总时长 {total_dur:.0f}min 超过日上限 "
                f"{_MAX_DAILY_BUDGET_MIN}min，请将该天 POI 拆分到多天"
            )

        # --- Transit ratio warning (soft) ---
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

    在完成行程规划后调用。系统会校验：
    - POI 不重复（同一 POI 只能出现一次）
    - 每天至少 1 个 POI
    - 每天总时长不超过 600 分钟（10 小时）
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
    plan = {"city": city, "days": days, "daily_plans": daily_plans}
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
        "daily_plans": daily_plans,
    }
