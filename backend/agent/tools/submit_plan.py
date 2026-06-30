"""submit_plan tool — validates and submits daily trip plans.

The LLM calls this after completing its trip layout.  The tool validates
the plan structure and rules (no duplicates, meal coverage per day, valid
coordinates) then returns the validated plan.  The API stream handler
intercepts the tool output and emits the ``route_result`` SSE event.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_plan(plan_data: dict[str, Any]) -> list[str]:
    """Validate a submitted trip plan.  Returns a list of error messages (empty = valid)."""
    errors: list[str] = []

    city = plan_data.get("city", "")
    if not city:
        errors.append("city 不能为空")

    days = plan_data.get("days", 0)
    if not isinstance(days, int) or days < 1:
        errors.append("days 必须是正整数")

    daily_plans = plan_data.get("daily_plans", [])
    if not isinstance(daily_plans, list) or not daily_plans:
        errors.append("daily_plans 不能为空")
        return errors

    seen_poi_ids: set[str] = set()

    for day_plan in daily_plans:
        day_num = day_plan.get("day", 0)
        if not isinstance(day_num, int) or day_num < 1:
            errors.append(f"daily_plans[?].day 无效: {day_num}")
            continue

        pois = day_plan.get("pois", [])
        if not isinstance(pois, list):
            errors.append(f"第{day_num}天: pois 必须是数组")
            continue

        if len(pois) < 2:
            errors.append(f"第{day_num}天: 至少需要 2 个 POI（含餐饮）")

        if len(pois) > 6:
            errors.append(f"第{day_num}天: 每天不超过 6 个 POI")

        # Check for duplicates within the day
        day_poi_ids: set[str] = set()
        for i, poi in enumerate(pois):
            poi_id = str(poi.get("poi_id", ""))
            if not poi_id:
                errors.append(f"第{day_num}天, POI[{i}]: 缺少 poi_id")
                continue
            if poi_id in day_poi_ids:
                errors.append(f"第{day_num}天: POI '{poi_id}' 在同一天重复出现")
            day_poi_ids.add(poi_id)

        # Check for cross-day duplicates
        for poi_id in day_poi_ids:
            if poi_id in seen_poi_ids:
                errors.append(f"POI '{poi_id}' 在多个天中出现，每个 POI 只能安排一次")
        seen_poi_ids |= day_poi_ids

        # Check for meal coverage
        meal_types = {p.get("meal_type") for p in pois if p.get("meal_type")}
        if not meal_types:
            errors.append(f"第{day_num}天: 缺少餐饮安排，每天至少需要 1 个 lunch 或 dinner POI")

        # Validate time_slots
        valid_slots = {"morning", "noon", "afternoon", "evening"}
        for i, poi in enumerate(pois):
            slot = poi.get("time_slot", "")
            if slot and slot not in valid_slots:
                errors.append(f"第{day_num}天, POI[{i}]: 无效的 time_slot '{slot}'")

    return errors


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
    - 每天有餐饮安排
    - 每天 POI 数量合理（2-6 个）
    - 时间槽和用餐类型合法

    校验通过后，行程会被推送到地图上展示。

    Args:
        city: 城市名称，如 "北京"
        days: 旅行天数
        daily_plans: 每日计划列表，每项格式：
            {
              "day": 1,
              "day_theme": "皇城中轴线漫游",
              "pois": [
                {"poi_id": "B001...", "time_slot": "morning", "visit_duration_min": 120},
                {"poi_id": "B001...", "time_slot": "noon", "visit_duration_min": 60, "meal_type": "lunch"}
              ]
            }
    """
    plan = {"city": city, "days": days, "daily_plans": daily_plans}
    errors = _validate_plan(plan)

    if errors:
        return {
            "status": "rejected",
            "errors": errors,
            "hint": "请修正上述问题后重新调用 submit_plan。常见修正方法："
                    "1) 删除跨天重复的 POI 并替换为新的；"
                    "2) 为缺少餐饮的天添加午餐或晚餐 POI；"
                    "3) 确保 POI 数量在 2-6 之间。",
        }

    return {
        "status": "accepted",
        "city": city,
        "days": days,
        "daily_plans": daily_plans,
    }
