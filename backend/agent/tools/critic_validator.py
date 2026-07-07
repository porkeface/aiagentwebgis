"""Multi-round Critic LLM validation for trip plans.

After the pipeline generates daily plans, the Critic LLM verifies:
1. Geographic coherence — POIs in same day are reasonably close
2. Time allocation — visit durations + transit fit within daily budget
3. Pace rhythm — not too packed or too empty
4. Opening hours — POIs are visitable during the planned period
5. Rating quality — low-rated spots are justified

Returns a verdict with optional corrections.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """你是一个严格的旅游行程审核专家。审查以下{days}日游{city}行程计划，检查合理性。

审核维度：
1. **地理连贯性**：同天的POI是否在合理的区域内？跨区穿梭是否严重？
2. **时间分配**：每个POI的游玩时长(visit_duration_min)是否合理？总时间+交通时间是否超出日预算(810分钟=13.5小时, 8:30-22:00)？
3. **节奏合理**：是否有某天太赶(>7个长时长POI)或太闲(只有1-2个短时长POI)？
4. **开放时间**：如果有opentime信息，POI的游玩是否在开放时间内？特别是博物馆（周一闭馆）？
5. **评分质量**：是否有评分低于3.5的POI可以替换？

请给出:
- overall: "pass" 或 "fail"
- issues: 发现的问题列表（如果有），每个包含 day/poi/severity("warn"|"error")/description
- suggestions: 改进建议列表（如果有），每个包含 action("swap"/"reorder"/"remove"/"add")/day/description
- score: 0-100 质量分数

返回纯JSON（不要markdown代码块）：
{{"overall": "pass", "issues": [], "suggestions": [], "score": 85}}"""

CRITIC_MAX_ROUNDS = 2


def _build_day_summary(day_plan: dict[str, Any]) -> str:
    """Build a text summary of one day for LLM consumption."""
    day_num = day_plan.get("day", "?")
    theme = day_plan.get("day_theme", "")
    total_dur = day_plan.get("total_duration_min", 0) or 0
    total_transit = day_plan.get("total_transit_min", 0) or 0

    lines = [f"--- Day {day_num}{' — ' + theme if theme else ''} ---"]
    lines.append(f"总游玩: {total_dur}min | 交通: {total_transit}min | 总计: {total_dur + total_transit}min")

    for i, poi in enumerate(day_plan.get("pois", [])):
        name = poi.get("name", "?")
        dur = poi.get("visit_duration_min", "?")
        rating = poi.get("rating", "?")
        addr = poi.get("address", "")[:20]
        cat = poi.get("category") or poi.get("type", "")
        opentime = poi.get("opentime", "")
        cost = poi.get("cost", "")
        importance = poi.get("importance", "")

        meta_parts = []
        if rating and rating != "?":
            meta_parts.append(f"评分{rating}")
        if dur and dur != "?":
            meta_parts.append(f"{dur}min")
        if importance:
            meta_parts.append(importance)
        if opentime:
            meta_parts.append(f"开放:{opentime}")
        if cost:
            meta_parts.append(cost)
        meta = ", ".join(meta_parts)

        lines.append(f"  [{i+1}] {name} ({cat}) | {meta}")
        if addr:
            lines.append(f"      地址: {addr}")

    return "\n".join(lines)


async def critic_review(
    daily_plans: list[dict[str, Any]],
    city: str = "",
    days: int = 0,
) -> dict[str, Any]:
    """Review a trip plan and return verdict with suggestions.

    Returns:
        {"overall": "pass"|"fail", "issues": [...], "suggestions": [...], "score": int}
    """
    plan_text = "\n\n".join(_build_day_summary(dp) for dp in daily_plans)

    prompt = CRITIC_PROMPT.format(city=city, days=days)
    user_msg = f"需要审核的行程：\n\n{plan_text}"

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0.0,
            timeout=30,
            max_retries=1,
        )
        response = await model.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_msg),
        ])
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rstrip("```").strip()

        result = json.loads(content)
        logger.info(
            "Critic review: overall=%s score=%d issues=%d suggestions=%d",
            result.get("overall"), result.get("score", 0),
            len(result.get("issues", [])), len(result.get("suggestions", [])),
        )
        return result
    except json.JSONDecodeError:
        logger.warning("Critic LLM returned invalid JSON: %.200s", content[:200] if 'content' in locals() else "<none>")
        return {"overall": "fail", "issues": [{"severity": "error", "description": "审核结果解析失败，请人工检查"}], "suggestions": [], "score": 0}
    except Exception as exc:
        logger.warning("Critic LLM call failed: %s", exc.__class__.__name__)
        return {"overall": "fail", "issues": [{"severity": "error", "description": "审核服务暂时不可用，请人工检查"}], "suggestions": [], "score": 0}


def _apply_suggestions(
    daily_plans: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    all_pois: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply the critic's suggestions to the daily plans.

    Currently handles:
    - remove: Remove a POI from a day
    - reorder: Swap day assignment (simple version — move to nearest day)
    """
    import copy
    updated = copy.deepcopy(daily_plans)

    for sug in suggestions:
        action = sug.get("action", "")
        target_day = sug.get("day")
        target_poi = sug.get("poi", "")
        description = sug.get("description", "")

        if action == "remove" and target_day is not None:
            for dp in updated:
                if dp.get("day") == target_day:
                    old_pois = dp.get("pois", [])
                    dp["pois"] = [p for p in old_pois if p.get("name") != target_poi]
                    removed_count = len(old_pois) - len(dp["pois"])
                    logger.info("Critic applied: removed '%s' from day %d (%d→%d POIs) — %s",
                                target_poi, target_day, len(old_pois), len(dp["pois"]), description)
                    break

        elif action == "reorder" and target_day is not None:
            new_day = sug.get("to_day", target_day)
            for dp in updated:
                if dp.get("day") == target_day:
                    old_pois = dp.get("pois", [])
                    moved = [p for p in old_pois if p.get("name") == target_poi]
                    dp["pois"] = [p for p in old_pois if p.get("name") != target_poi]
                    if moved:
                        for tdp in updated:
                            if tdp.get("day") == new_day:
                                tdp["pois"].append(moved[0])
                                logger.info("Critic applied: moved '%s' day %d→%d — %s",
                                            target_poi, target_day, new_day, description)
                                break
                    break

        elif action == "swap":
            # Replace with an alternative POI from the pool
            if not all_pois:
                continue
            alternative_name = sug.get("alternative", "")
            if not alternative_name:
                continue
            # Find alternative in the pool
            alt_poi = None
            for p in all_pois:
                if p.get("name", "").lower() == alternative_name.lower():
                    alt_poi = p
                    break
            if not alt_poi:
                # Fuzzy match — any POI containing the keyword
                for p in all_pois:
                    if alternative_name.lower() in (p.get("name", "") or "").lower():
                        alt_poi = p
                        break
            if alt_poi:
                for dp in updated:
                    if dp.get("day") == target_day:
                        old_pois = dp.get("pois", [])
                        dp["pois"] = [
                            alt_poi if p.get("name") == target_poi else p
                            for p in old_pois
                        ]
                        logger.info("Critic applied: swapped '%s'→'%s' on day %d — %s",
                                    target_poi, alt_poi.get("name"), target_day, description)
                        break

    return updated


def _prune_empty_days(daily_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove days with zero POIs and renumber remaining days sequentially."""
    non_empty = [dp for dp in daily_plans if len(dp.get("pois", [])) > 0]
    if len(non_empty) == len(daily_plans):
        return daily_plans
    for i, dp in enumerate(non_empty, start=1):
        dp["day"] = i
    logger.info("Critic: pruned %d empty day(s), %d remain",
                len(daily_plans) - len(non_empty), len(non_empty))
    return non_empty


async def run_critic_loop(
    daily_plans: list[dict[str, Any]],
    city: str = "",
    days: int = 0,
    all_pois: list[dict[str, Any]] | None = None,
    writer=None,
) -> list[dict[str, Any]]:
    """Run critic review rounds, applying fixes until pass or max rounds reached.

    Returns the (potentially improved) daily_plans.
    """
    for round_num in range(1, CRITIC_MAX_ROUNDS + 1):
        if writer:
            writer({
                "type": "critic_review",
                "data": {"round": round_num, "message": f"第{round_num}轮质量审核中..."},
            })

        verdict = await critic_review(daily_plans, city=city, days=days)

        if writer:
            writer({
                "type": "critic_result",
                "data": {
                    "overall": verdict.get("overall"),
                    "score": verdict.get("score"),
                    "issue_count": len(verdict.get("issues", [])),
                    "suggestion_count": len(verdict.get("suggestions", [])),
                },
            })

        if verdict.get("overall") == "pass" or not verdict.get("suggestions"):
            break

        # Apply suggestions
        daily_plans = _apply_suggestions(
            daily_plans,
            verdict.get("suggestions", []),
            all_pois or [],
        )

        # Prune any days that became empty after removals
        daily_plans = _prune_empty_days(daily_plans)

    return daily_plans
