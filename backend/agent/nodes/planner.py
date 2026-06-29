"""Planner Node — ReAct-style travel planning agent.

Extracts trip parameters (city, days) from the user's message,
sets default recommendation weights based on companion types,
builds a prompt, calls the LLM, and stores the response text.
"""

from __future__ import annotations

import re
from typing import Any

from agent.llm.base import BaseLLMAdapter
from agent.state import AgentState


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


# ---------------------------------------------------------------------------
# Chinese number mapping
# ---------------------------------------------------------------------------

_CN_NUM: dict[str, int] = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# Known cities that don't end with 市
_KNOWN_CITIES: frozenset[str] = frozenset({
    "北京", "上海", "杭州", "南京", "成都", "重庆", "西安",
    "广州", "深圳", "苏州", "天津", "武汉", "长沙", "青岛",
    "厦门", "昆明", "大理", "丽江", "三亚", "桂林",
})

# Regex: Chinese city name ending with 市 (2-4 chars before 市)
_RE_CITY_SHI = re.compile(r"([一-龥]{2,4}市)")

# Regex: known city name
_RE_KNOWN_CITY = re.compile(
    r"(" + "|".join(sorted(_KNOWN_CITIES, key=len, reverse=True)) + r")"
)

# Regex: N天/日游 with Chinese number
_RE_DAYS_CN = re.compile(r"([一二两三四五六七八九十])[天日]")

# Regex: N天 with Arabic number
_RE_DAYS_ARABIC = re.compile(r"(\d+)\s*天")

# Regex: 一日游 pattern
_RE_ONE_DAY_TRIP = re.compile(r"一日游")


# ---------------------------------------------------------------------------
# PlannerNode
# ---------------------------------------------------------------------------


class PlannerNode:
    """ReAct-style planner that extracts params and calls LLM."""

    def __init__(self, llm_adapter: BaseLLMAdapter) -> None:
        """Initialize with an LLM adapter.

        Args:
            llm_adapter: Adapter implementing BaseLLMAdapter interface.
        """
        self._adapter = llm_adapter

    async def plan(self, state: AgentState) -> AgentState:
        """Main planner entry point.

        Extracts trip parameters, ensures weights are set,
        builds messages, calls the LLM, and returns updated state.

        Args:
            state: Current agent state.

        Returns:
            New AgentState with extracted params and response_text set.
        """
        # 1. Extract city and days from last user message
        params = self._extract_params(state)

        # 2. Ensure recommendation weights are populated
        state = self._ensure_weights(state)

        # 3. Build updated state with extracted params
        updated: AgentState = {
            **state,
            **{k: v for k, v in params.items() if v is not None},
        }

        # 4. Build messages list
        messages = self._build_messages(updated)

        # 5. Call LLM
        response = await self._adapter.chat(messages)

        # 6. Return new state with response_text
        return {**updated, "response_text": response.content}

    def _extract_params(self, state: AgentState) -> dict[str, Any]:
        """Extract city and days from the last user message.

        Args:
            state: Current agent state with messages list.

        Returns:
            Dict with 'city' and 'days' keys (values may be None).
        """
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
        """Extract city name from text.

        Checks for 'X市' pattern first, then known city names.

        Args:
            text: User input text.

        Returns:
            City name string or None.
        """
        if not text:
            return None

        # Try 'X市' pattern first
        match = _RE_CITY_SHI.search(text)
        if match:
            return match.group(1)

        # Try known cities
        match = _RE_KNOWN_CITY.search(text)
        if match:
            return match.group(1)

        return None

    def _extract_days(self, text: str) -> int | None:
        """Extract number of days from text.

        Handles Chinese numbers (两天, 三日) and Arabic numbers (3天).
        Also handles 一日游 pattern.

        Args:
            text: User input text.

        Returns:
            Number of days or None.
        """
        if not text:
            return None

        # Arabic number pattern: 3天, 5 天
        match = _RE_DAYS_ARABIC.search(text)
        if match:
            return int(match.group(1))

        # Chinese number pattern: 两天, 三日
        match = _RE_DAYS_CN.search(text)
        if match:
            cn_char = match.group(1)
            return _CN_NUM.get(cn_char)

        # 一日游 pattern
        if _RE_ONE_DAY_TRIP.search(text):
            return 1

        return None

    def _ensure_weights(self, state: AgentState) -> AgentState:
        """Set default recommendation weights if not already present.

        Adjusts weights based on companion_types:
        - elderly: lower distance, lower time
        - children: lower distance, higher popularity
        - default: balanced weights

        Args:
            state: Current agent state.

        Returns:
            New state with recommendation_weights populated if needed.
        """
        if state.get("recommendation_weights") is not None:
            return state

        companion_types = state.get("companion_types", [])
        weights = self._default_weights(companion_types)

        return {**state, "recommendation_weights": weights}

    @staticmethod
    def _default_weights(companion_types: list[str]) -> dict[str, float]:
        """Calculate default weights based on companion types.

        Args:
            companion_types: List of companion type strings.

        Returns:
            Weight dict summing to 1.0.
        """
        if "elderly" in companion_types:
            return {
                "preference": 0.30,
                "distance": 0.15,
                "rating": 0.15,
                "time": 0.25,
                "popularity": 0.15,
            }

        if "children" in companion_types:
            return {
                "preference": 0.25,
                "distance": 0.15,
                "rating": 0.15,
                "time": 0.15,
                "popularity": 0.30,
            }

        return {
            "preference": 0.30,
            "distance": 0.20,
            "rating": 0.20,
            "time": 0.15,
            "popularity": 0.15,
        }

    @staticmethod
    def _build_messages(state: AgentState) -> list[dict[str, Any]]:
        """Build the messages list for the LLM call.

        Prepends the system prompt to the conversation history.

        Args:
            state: Agent state containing messages.

        Returns:
            List of message dicts with system prompt prepended.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        messages.extend(state.get("messages", []))
        return messages
