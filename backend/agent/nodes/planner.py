"""Planner Node — Real travel planning with spatial analysis pipeline.

Pipeline:
1. Extract city, days, preferences from user input
2. Search POIs (Amap API → DB fallback)
3. Multi-factor scoring (preference, distance, rating, popularity)
4. Select top POIs per day
5. Generate daily plans with routes
6. Call LLM for text response
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from typing import Any

from agent.llm.base import BaseLLMAdapter
from agent.state import AgentState
from agent.tools.poi_search import search_pois_tool
from agent.tools.spatial_analysis import score_pois_tool, _haversine_km
from agent.tools.route_planning import plan_route_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "你是一位专业的旅行规划助手。你的职责是根据用户的需求，"
    "帮助他们规划旅行行程、推荐景点和美食、安排每日行程路线。\n\n"
    "请遵循以下原则：\n"
    "1. 根据用户提到的城市和天数，生成合理的行程安排。\n"
    "2. 每天的景点安排要考虑地理位置的合理性，避免来回奔波。\n"
    "3. 推荐当地特色美食和餐厅。\n"
    "4. 考虑同行人员（老人、儿童、情侣等）的特殊需求。\n"
    "5. 回答要简洁、有条理，使用中文回复。\n"
    "6. 如果用户没有指定天数，默认推荐2天行程。\n"
    "7. 可以适当给出交通建议和预算参考。"
)

# Used when the user is just chatting (intent=general) and no trip data
# exists to anchor the response. Keeps the same persona so the conversation
# stays consistent with the trip-planning mode.
CHAT_SYSTEM_PROMPT = (
    "你是 Travel Atlas —— 一位有温度的旅行助手。\n\n"
    "当用户没有给出具体行程需求时（只是在打招呼、问你能做什么、"
    "问推荐目的地、闲聊旅行心得、问天气/签证等小问题），你可以：\n"
    "1. 用友好、轻松的语气回应，像一位熟悉各地的朋友。\n"
    "2. 主动介绍你的能力：告诉用户你可以基于城市、天数、主题偏好"
    "（美食/文化/亲子/夜景/小众等）规划完整行程，并把 POI 标在地图上。\n"
    "3. 如果用户提到一个城市但没说天数/主题，可以反问 1-2 个澄清问题"
    "（想去几天？偏好什么主题？和谁一起去？），引导他们给出可执行的需求。\n"
    "4. 回答简洁、有条理，使用中文，控制在 4 段以内。\n"
    "5. 不要编造不存在的 POI 名或具体路线 —— 那是行程模式才做的事。"
)


# ---------------------------------------------------------------------------
# Chinese number mapping
# ---------------------------------------------------------------------------
# Supports both single-digit (一, 二 ...) and compound (二十, 三十二, 一百,
# 一百二十五). "百" and "千" are tracked but not yet wired into _cn_to_int —
# we only need day-count precision up to a reasonable upper bound (a 100-day
# trip is unusual but possible).

_CN_NUM: dict[str, int] = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100, "千": 1000,
}

# Known cities that don't end with 市
_KNOWN_CITIES: frozenset[str] = frozenset({
    "北京", "上海", "杭州", "南京", "成都", "重庆", "西安",
    "广州", "深圳", "苏州", "天津", "武汉", "长沙", "青岛",
    "厦门", "昆明", "大理", "丽江", "三亚", "桂林",
})

# City regex: prefer matching a known city name; fall back to a generic
# "<chars>市" pattern. We don't use a lookbehind for "<chinese-char>" because
# Chinese text rarely has natural word boundaries — every city name is
# flanked by other Chinese characters in realistic inputs (e.g. "打算去三亚",
# "算去北京市旅游"). Instead we lean on the KNOWN_CITIES list and the fact
# that "X市" is the official administrative suffix.
_RE_CITY_SHI = re.compile(r"([一-龥]{2,4}市)")
_RE_KNOWN_CITY = re.compile(
    r"(" + "|".join(sorted(_KNOWN_CITIES, key=len, reverse=True)) + r")"
)
# Days regex: supports compound Chinese numbers like 二十, 三十二, 一百,
# 一百二十五, etc. Pattern explanation:
#   (?:[一二两三四五六七八九]?百)?   — optional hundreds prefix (1-9 + 百)
#   (?:[一二两三四五六七八九]?十)? — optional tens prefix (1-9 + 十, may be bare 十)
#   [一二两三四五六七八九]?         — optional ones digit
# followed by [天日] as the day-count suffix.
_RE_DAYS_CN = re.compile(
    r"((?:[一二两三四五六七八九]?百)?"
    r"(?:[一二两三四五六七八九]?十)?"
    r"[一二两三四五六七八九]?)"
    r"[天日]"
)
_RE_DAYS_ARABIC = re.compile(r"(\d+)\s*天")
_RE_ONE_DAY_TRIP = re.compile(r"一日游")

# Default POIs per day
_POIS_PER_DAY = 3
DEFAULT_DAYS = 2
# Generous upper bound. Real trips rarely exceed 30 days, but the agent
# shouldn't silently truncate "我想去一百天" or "a 60-day Europe trip" —
# the user explicitly asked for that many days, so honor it. The frontend
# UI can warn / suggest splitting into separate trips if desired.
DEFAULT_DAYS_MAX = 365


def _cn_to_int(s: str) -> int | None:
    """Convert a (possibly compound) Chinese day-string to int.

    Handles the forms we actually see in user input:
      ''      -> None
      '三'    -> 3          (single digit)
      '十五'  -> 15         (十 + ones, empty tens = 1)
      '三十二'-> 32         (tens + ones)
      '三十'  -> 30         (tens + missing ones = 0)
      '一百'  -> 100        (百 with no tens/ones)
      '一百二十五' -> 125   (百 + tens + ones)
      '两百'  -> 200        (两百 is colloquial for 二百)

    Limited to two-digit hundreds (max 999) since trips over that length are
    handled by the upstream regex's < 999 chars cap.
    """
    if not s:
        return None

    # ----- "百" path -----
    if "百" in s:
        # Split around 百, fall back to default multipliers if missing.
        parts = s.split("百")
        hundreds_str = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        hundreds = _CN_NUM.get(hundreds_str, 1) if hundreds_str else 1
        # Recurse on the remainder (which may contain 十 / ones).
        rest_value = _cn_to_int(rest) or 0
        return hundreds * 100 + rest_value

    # ----- "十" path -----
    if "十" in s:
        parts = s.split("十")
        tens_str = parts[0]
        tens_digit = _CN_NUM.get(tens_str, 1) if tens_str else 1
        ones_str = parts[1] if len(parts) > 1 else ""
        ones_digit = _CN_NUM.get(ones_str, 0) if ones_str else 0
        return tens_digit * 10 + ones_digit

    # ----- single-digit path -----
    return _CN_NUM.get(s)


# ---------------------------------------------------------------------------
# PlannerNode
# ---------------------------------------------------------------------------


class PlannerNode:
    """Planner that extracts params, searches POIs, scores, and plans routes."""

    def __init__(self, llm_adapter: BaseLLMAdapter) -> None:
        self._adapter = llm_adapter

    async def plan(self, state: AgentState) -> AgentState:
        """Main planner entry point.

        Full pipeline:
        1. Extract trip parameters
        2. Search POIs for the city (skipped for general intent)
        3. Score and select POIs (using user-specified weights)
        4. Build daily plans with geographic clustering
        5. Generate route polylines (parallel)
        6. Call LLM for text response

        Args:
            state: Current agent state.

        Returns:
            New AgentState with all planning fields populated.
        """
        # 1. Extract city and days
        params = self._extract_params(state)

        # 2. Ensure recommendation weights
        state = self._ensure_weights(state)

        # 3. Build updated state
        updated: AgentState = {
            **state,
            **{k: v for k, v in params.items() if v is not None},
        }

        city = updated.get("city")
        days = updated.get("days")
        intent = updated.get("intent", "trip_planning")

        # 4. Search POIs if city is known and intent is not general chat
        candidate_pois: list[dict[str, Any]] = []
        if city and intent != "general":
            candidate_pois = await self._search_and_score_pois(city, updated)
            updated = {**updated, "candidate_pois": candidate_pois}

        # 5. Select POIs and build daily plans (geographic clustering)
        selected_pois: list[dict[str, Any]] = []
        daily_plans: list[dict[str, Any]] = []
        route_polylines: list[dict[str, Any]] = []

        # Don't plan more days than we have POIs; otherwise several days will
        # share the same seed POI and the map shows repeated stops.
        if candidate_pois:
            requested_days = max(1, min(days or DEFAULT_DAYS, DEFAULT_DAYS_MAX))
            n_days = min(requested_days, max(1, len(candidate_pois) // _POIS_PER_DAY + 1))
            n_days = min(n_days, len(candidate_pois)) if candidate_pois else n_days
            selected_pois = self._select_top_pois(candidate_pois, n_days * _POIS_PER_DAY)
            daily_plans, route_polylines = await self._build_daily_plans(
                selected_pois, n_days, city,
            )
            updated = {
                **updated,
                "selected_pois": selected_pois,
                "daily_plans": daily_plans,
                "route_polylines": route_polylines,
            }

        # 6. Call LLM for text response — feed the just-planned POIs back
        # into the context so the LLM doesn't make up generic text that
        # contradicts the map data.
        messages = self._build_messages(updated)
        response = await self._adapter.chat(messages)

        return {**updated, "response_text": response.content}

    # -----------------------------------------------------------------------
    # POI Search & Scoring
    # -----------------------------------------------------------------------

    async def _search_and_score_pois(
        self, city: str, state: AgentState,
    ) -> list[dict[str, Any]]:
        """Search POIs for the city and score them.

        Tries multiple categories to get diverse results.
        Falls back to DB if Amap API is unavailable.

        Args:
            city: Target city name.
            state: Agent state with preferences and weights.

        Returns:
            Scored and deduplicated POI list.
        """
        # Use Chinese categories for Amap API; DB fallback maps to English internally
        categories = ["景点", "美食", "购物", "休闲娱乐"]
        all_pois: list[dict[str, Any]] = []
        seen_ids: set = set()

        for category in categories:
            try:
                pois = await search_pois_tool(city=city, category=category)
                for poi in pois:
                    poi_id = poi.get("id", poi.get("amap_id", ""))
                    if poi_id not in seen_ids:
                        seen_ids.add(poi_id)
                        all_pois.append(poi)
            except Exception as e:
                logger.warning(f"Search failed for {city}/{category}: {e}")

        if not all_pois:
            logger.info(f"No POIs found for city={city}")
            return []

        preferences = state.get("preferences", [])
        weights = state.get("recommendation_weights")

        # Compute the city center from candidate POIs so the distance score
        # is meaningful. Without this, score_pois_tool's distance factor
        # silently degrades to neutral (0.5) for every POI.
        center = _city_center(all_pois)

        # Score POIs with user-specified weights (H2 fix)
        scored = score_pois_tool(
            pois=all_pois,
            preferences=preferences,
            weights=weights,
            city_center_lng=center[0],
            city_center_lat=center[1],
        )

        # Sort by score descending
        scored.sort(key=lambda p: p.get("score", 0), reverse=True)
        logger.info(f"Found {len(scored)} POIs for {city}, scored and sorted")
        return scored

    def _select_top_pois(
        self, pois: list[dict[str, Any]], max_count: int,
    ) -> list[dict[str, Any]]:
        """Select top POIs by score.

        Args:
            pois: Scored POI list (sorted by score desc).
            max_count: Maximum number to select.

        Returns:
            Top N POIs.
        """
        return pois[:max_count]

    # -----------------------------------------------------------------------
    # Daily Plan Builder
    # -----------------------------------------------------------------------

    async def _build_daily_plans(
        self,
        pois: list[dict[str, Any]],
        n_days: int,
        city: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Distribute POIs into daily plans with routes.

        Uses greedy nearest-neighbor clustering so each day's POIs are
        geographically close. Route segments are planned in parallel
        via asyncio.gather.

        Args:
            pois: Selected POIs (sorted by score).
            n_days: Number of trip days.
            city: City name (for route labels).

        Returns:
            Tuple of (daily_plans, route_polylines).
        """
        if not pois:
            return [], []

        # --- Geographic clustering (greedy nearest-neighbor) ---
        daily_groups = self._cluster_pois_by_geo(pois, n_days)

        # --- Collect all route segments to plan (for parallel execution) ---
        route_tasks: list[tuple[int, int, dict[str, Any]]] = []
        # (day_number, segment_index, segment_meta)

        day_segment_indices: dict[int, list[int]] = {}
        global_idx = 0

        for day_idx, day_pois in enumerate(daily_groups):
            if not day_pois:
                continue
            day_number = day_idx + 1
            indices = []
            for _i in range(len(day_pois) - 1):
                origin_lng = day_pois[_i].get("lng", 0.0)
                origin_lat = day_pois[_i].get("lat", 0.0)
                dest_lng = day_pois[_i + 1].get("lng", 0.0)
                dest_lat = day_pois[_i + 1].get("lat", 0.0)
                if origin_lng and origin_lat and dest_lng and dest_lat:
                    route_tasks.append((
                        day_number,
                        _i,
                        {
                            "from_poi": day_pois[_i],
                            "to_poi": day_pois[_i + 1],
                            "origin_lng": origin_lng,
                            "origin_lat": origin_lat,
                            "dest_lng": dest_lng,
                            "dest_lat": dest_lat,
                        },
                    ))
                    indices.append(global_idx)
                    global_idx += 1
            day_segment_indices[day_idx] = indices

        # --- Execute all route plans in parallel (H8 fix) ---
        route_results = await asyncio.gather(
            *[
                self._plan_single_route(task[2]["origin_lng"], task[2]["origin_lat"],
                                        task[2]["dest_lng"], task[2]["dest_lat"])
                for task in route_tasks
            ],
            return_exceptions=True,
        )

        # --- Build final daily plans ---
        daily_plans: list[dict[str, Any]] = []
        all_polylines: list[dict[str, Any]] = []

        for day_idx, day_pois in enumerate(daily_groups):
            if not day_pois:
                continue

            day_number = day_idx + 1
            seg_indices = day_segment_indices.get(day_idx, [])

            day_polylines: list[dict[str, Any]] = []
            total_distance = 0.0

            for local_i, global_i in enumerate(seg_indices):
                result = route_results[global_i]
                meta = route_tasks[global_i][2]
                from_poi = meta["from_poi"]
                to_poi = meta["to_poi"]
                origin_lng = meta["origin_lng"]
                origin_lat = meta["origin_lat"]
                dest_lng = meta["dest_lng"]
                dest_lat = meta["dest_lat"]

                polyline = {
                    "day": day_number,
                    "from_poi_id": from_poi.get("id"),
                    "from_name": from_poi.get("name", ""),
                    "from_lng": origin_lng,
                    "from_lat": origin_lat,
                    "to_poi_id": to_poi.get("id"),
                    "to_name": to_poi.get("name", ""),
                    "to_lng": dest_lng,
                    "to_lat": dest_lat,
                    "distance_km": 0.0,
                    "duration_min": 0,
                    "coordinates": [
                        [origin_lat, origin_lng],
                        [dest_lat, dest_lng],
                    ],
                }

                if isinstance(result, Exception):
                    logger.debug(f"Route planning failed (parallel): {result}")
                    dist = _haversine_km(origin_lng, origin_lat, dest_lng, dest_lat)
                    polyline["distance_km"] = round(dist, 2)
                    polyline["duration_min"] = round(dist * 12)
                    total_distance += dist
                elif isinstance(result, dict):
                    polyline["distance_km"] = result.get("distance_km", 0.0)
                    polyline["duration_min"] = result.get("duration_min", 0)
                    if result.get("polyline"):
                        polyline["coordinates"] = result["polyline"]
                    total_distance += polyline["distance_km"]

                day_polylines.append(polyline)

            day_plan = {
                "day": day_number,
                "day_title": f"第{day_number}天",
                "pois": [
                    {
                        "id": poi.get("id", 0),
                        "name": poi.get("name", ""),
                        "category": poi.get("category", ""),
                        "address": poi.get("address"),
                        "lng": poi.get("lng", 0.0),
                        "lat": poi.get("lat", 0.0),
                        "rating": poi.get("rating"),
                        "tags": poi.get("tags", []),
                        "score": poi.get("score", 0),
                        "photo": poi.get("photo"),
                        "description": poi.get("description"),
                    }
                    for poi in day_pois
                ],
                "total_distance_km": round(total_distance, 2),
            }

            daily_plans.append(day_plan)
            all_polylines.extend(day_polylines)

        logger.info(
            f"Built {len(daily_plans)} daily plans with "
            f"{len(all_polylines)} route segments for {city}"
        )
        return daily_plans, all_polylines

    @staticmethod
    def _cluster_pois_by_geo(
        pois: list[dict[str, Any]], n_days: int,
    ) -> list[list[dict[str, Any]]]:
        """Cluster POIs into daily groups using greedy nearest-neighbor.

        Seeds each day's group from a geographically spread starting point
        (evenly-spaced by latitude), then assigns remaining POIs to the
        nearest day centroid.

        Args:
            pois: Scored POI list.
            n_days: Number of days/groups.

        Returns:
            List of n_days lists, each containing POI dicts.
        """
        if not pois:
            return [[] for _ in range(n_days)]
        if n_days <= 1:
            return [list(pois)]

        # Clamp n_days to the number of distinct seeds we can produce.
        # Without this, when len(pois) < n_days the same seed POI ends up in
        # multiple groups and the map shows the same stop repeated across days.
        effective_days = min(n_days, len(pois))
        if effective_days <= 1:
            return [list(pois)]

        # Sort POIs by latitude for initial seeding
        sorted_pois = sorted(pois, key=lambda p: p.get("lat", 0.0))
        step = max(len(sorted_pois) // effective_days, 1)

        groups: list[list[dict[str, Any]]] = [[] for _ in range(effective_days)]
        assigned: set[int] = set()

        # Seed each group with a distinct POI. Skip POIs already assigned
        # (only happens when step is very small).
        for d in range(effective_days):
            for offset in range(len(sorted_pois)):
                seed_idx = min(d * step + offset, len(sorted_pois) - 1)
                seed_poi = sorted_pois[seed_idx]
                if id(seed_poi) in assigned:
                    continue
                groups[d].append(seed_poi)
                assigned.add(id(seed_poi))
                break

        # Compute centroids and assign remaining POIs by nearest centroid
        remaining = [p for p in pois if id(p) not in assigned]

        def _centroid(grp: list[dict[str, Any]]) -> tuple[float, float]:
            if not grp:
                return (0.0, 0.0)
            avg_lng = sum(p.get("lng", 0.0) for p in grp) / len(grp)
            avg_lat = sum(p.get("lat", 0.0) for p in grp) / len(grp)
            return (avg_lng, avg_lat)

        for poi in remaining:
            best_day = 0
            best_dist = math.inf
            poi_lng = poi.get("lng", 0.0)
            poi_lat = poi.get("lat", 0.0)
            for d in range(effective_days):
                c_lng, c_lat = _centroid(groups[d])
                dist = _haversine_km(poi_lng, poi_lat, c_lng, c_lat)
                if dist < best_dist:
                    best_dist = dist
                    best_day = d
            groups[best_day].append(poi)

        # Sort each group by longitude for a sensible visit order
        for grp in groups:
            grp.sort(key=lambda p: p.get("lng", 0.0))

        # Pad to the requested n_days with empty lists so downstream code
        # (formatter, save_plan) can rely on the shape.
        while len(groups) < n_days:
            groups.append([])

        return groups

    @staticmethod
    async def _plan_single_route(
        origin_lng: float, origin_lat: float,
        dest_lng: float, dest_lat: float,
    ) -> dict[str, Any]:
        """Plan a single route segment (wrapper for parallel execution).

        Falls back to straight-line haversine distance on failure.

        Returns:
            Dict with distance_km, duration_min, and optional polyline.
        """
        try:
            result = await plan_route_tool(
                origin_lng=origin_lng,
                origin_lat=origin_lat,
                dest_lng=dest_lng,
                dest_lat=dest_lat,
            )
            return result
        except Exception as e:
            logger.debug(f"Route planning failed: {e}")
            dist = _haversine_km(origin_lng, origin_lat, dest_lng, dest_lat)
            return {
                "distance_km": round(dist, 2),
                "duration_min": round(dist * 12),
            }

    # -----------------------------------------------------------------------
    # Parameter Extraction (reused from original)
    # -----------------------------------------------------------------------

    def _extract_params(self, state: AgentState) -> dict[str, Any]:
        messages = state.get("messages", [])
        last_user_text = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_text = msg.get("content", "")
                break

        city = self._extract_city(last_user_text)
        days = self._extract_days(last_user_text)
        return {"city": city, "days": days}

    def _extract_city(self, text: str) -> str | None:
        if not text:
            return None
        # Known cities first (longest match wins via the sorted-by-length-desc
        # pattern). Falls back to the generic X市 suffix for cities we don't
        # have in the explicit list. Strip the trailing 市 so it matches the
        # DB-stored city name (e.g. "北京市" -> "北京").
        match = _RE_KNOWN_CITY.search(text)
        if match:
            return match.group(1)
        match = _RE_CITY_SHI.search(text)
        if match:
            return match.group(1).rstrip("市")
        return None

    def _extract_days(self, text: str) -> int | None:
        if not text:
            return None
        match = _RE_DAYS_ARABIC.search(text)
        if match:
            value = int(match.group(1))
            return max(1, min(value, DEFAULT_DAYS_MAX))
        match = _RE_DAYS_CN.search(text)
        if match:
            value = _cn_to_int(match.group(1))
            if value is not None:
                return max(1, min(value, DEFAULT_DAYS_MAX))
        if _RE_ONE_DAY_TRIP.search(text):
            return 1
        return None

    def _ensure_weights(self, state: AgentState) -> AgentState:
        if state.get("recommendation_weights") is not None:
            return state
        companion_types = state.get("companion_types", [])
        weights = self._default_weights(companion_types)
        return {**state, "recommendation_weights": weights}

    @staticmethod
    def _default_weights(companion_types: list[str]) -> dict[str, float]:
        if "老年" in companion_types or "elderly" in companion_types:
            return {
                "preference": 0.30, "distance": 0.15, "rating": 0.15,
                "time": 0.25, "popularity": 0.15,
            }
        if "亲子" in companion_types or "children" in companion_types:
            return {
                "preference": 0.25, "distance": 0.15, "rating": 0.15,
                "time": 0.15, "popularity": 0.30,
            }
        return {
            "preference": 0.30, "distance": 0.20, "rating": 0.20,
            "time": 0.15, "popularity": 0.15,
        }

    @staticmethod
    def _build_messages(state: AgentState) -> list[dict[str, Any]]:
        intent = state.get("intent", "trip_planning")

        # Chat mode: no trip context to feed the LLM, and no POI/daily data
        # to inject. Use the chat-only system prompt so the model doesn't
        # try to fabricate a route.
        if intent == "general":
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT}
            ]
            messages.extend(state.get("messages", []))
            return messages

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Inject a structured summary of the planned trip (city, days, top
        # POIs by score, and per-day plan) so the LLM's text response
        # references the same data the map shows.
        context_parts: list[str] = []
        city = state.get("city")
        days = state.get("days")
        if city or days:
            context_parts.append(
                f"已规划行程: 城市={city or '未指定'}, 天数={days or '未指定'}"
            )

        candidate_pois = state.get("candidate_pois") or []
        if candidate_pois:
            top = sorted(
                candidate_pois,
                key=lambda p: p.get("score", 0),
                reverse=True,
            )[:10]
            poi_lines = [
                f"  - {p.get('name', '?')} (评分: {p.get('score', 0):.2f}, "
                f"类别: {p.get('category', '?')}, 地址: {p.get('address') or '无'})"
                for p in top
            ]
            context_parts.append("候选 POI (按评分排序,前10):\n" + "\n".join(poi_lines))

        daily_plans = state.get("daily_plans") or []
        for plan in daily_plans:
            day_pois = plan.get("pois", [])
            names = [p.get("name", "?") for p in day_pois]
            if names:
                context_parts.append(
                    f"第{plan.get('day', '?')}天: " + " → ".join(names)
                )

        if context_parts:
            messages.append({
                "role": "system",
                "content": "以下是系统已经规划好的真实数据,请基于这些数据回答用户,不要编造 POI 或路线:\n"
                + "\n".join(context_parts),
            })

        messages.extend(state.get("messages", []))
        return messages


def _city_center(pois: list[dict[str, Any]]) -> tuple[float, float]:
    """Return the geometric (lng, lat) centroid of the given POIs.

    Used as a reference point for distance scoring. Returns (0, 0) when the
    list is empty so callers can still pass a numeric value through.
    """
    valid = [
        (p.get("lng"), p.get("lat"))
        for p in pois
        if isinstance(p.get("lng"), (int, float))
        and isinstance(p.get("lat"), (int, float))
    ]
    if not valid:
        return (0.0, 0.0)
    avg_lng = sum(lng for lng, _ in valid) / len(valid)
    avg_lat = sum(lat for _, lat in valid) / len(valid)
    return (avg_lng, avg_lat)
