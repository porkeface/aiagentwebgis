"""Router Node for intent classification.

Classifies user messages into one of three intents:
- 'trip_planning': User wants to plan a trip/itinerary
- 'poi_recommendation': User asks for POI recommendations (food, sights, etc.)
- 'general': Greetings or general chat

This is the MVP keyword-based implementation. Future iterations may use
LLM-based classification for higher accuracy.
"""

import re

from agent.state import AgentState


# Keyword sets for intent classification. Keep the trip set focused on
# unambiguous verbs (规划/旅行/旅游) — words like "攻略" and "行程" are too
# common in POI queries (e.g. "北京美食攻略") so we require a stronger
# pattern match instead.
TRIP_KEYWORDS: frozenset[str] = frozenset({
    "规划", "旅行", "旅游", "路线规划",
    "行程安排", "怎么玩", "怎么走",
})

# Phrases that imply a multi-day itinerary, not a casual mention of "行程".
# We require these to be present before classifying as trip_planning, so that
# phrases like "我今天行程很赶" or "请问行程单号" don't get misrouted.
# Note: each pattern must require EITHER a day-count "X日游"/"X天 Y天"
# suffix OR a strong trip-verb+noun pair (e.g. "做一份攻略"). Bare mentions
# like "去上海" or "到上海" alone are NOT trip plans — the user is just
# naming a destination.
_TRIP_PHRASE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d+\s*日游"),
    re.compile(r"[一二两三四五六七八九十百千]+\s*[天日]\s*游"),
    re.compile(r"[一二两三四五六七八九十百千]+\s*[天日]\s*(?:行程|旅行|旅游|攻略)"),
    re.compile(r"(?:规划|安排|设计|做|做一份|出一份).{0,20}(?:行程|攻略|路线|旅行|旅游)"),
    # "去 <城市> <天数>[日游|天]" — requires a day count after the city,
    # otherwise patterns like "上海有哪些值得去的景点" get misclassified.
    re.compile(r"(?:去|到|去往|想去)\s*[一-龥A-Za-z]{2,8}\s*[一二两三四五六七八九十百千\d]+\s*[天日](?:游)?"),
    re.compile(r"(?:去|到|去往|想去)\s*[一-龥A-Za-z]{2,8}\s*\d+\s*日游"),
    re.compile(r"做(?:一份|个)?\s*[一-龥A-Za-z]{2,8}\s*(?:攻略|旅行|旅游)"),
    # "<城市> <天数>日/天 <主题>" — common editorial style: "北京五日，深度文化"
    # or "成都 3 天美食". Requires a city prefix (2-8 CJK chars) before the
    # number so that bare phrases like "三天后见" don't match.
    re.compile(r"[一-龥A-Za-z]{2,8}\s*[一二两三四五六七八九十百千\d]+\s*[天日](?:游)?[，,。]?\s*[一-龥A-Za-z]{2,}"),
    # "<天数>天/日 + 中文标点" alone (e.g. "3 天，深度文化") — but ONLY when
    # the number is at or near the start of the message.
    re.compile(r"^[一二两三四五六七八九十百千\d]+\s*[天日][，,。]\s*[一-龥A-Za-z]{2,}"),
)

# Words that look trip-related but are too common — kept as soft hints.
# They need to be paired with a stronger cue (city / day count / trip verb)
# to escalate to trip_planning.
TRIP_SOFT_HINTS: frozenset[str] = frozenset({
    "行程", "几天", "路线", "日程",
})

POI_KEYWORDS: frozenset[str] = frozenset({
    "推荐", "好吃", "好玩", "景点", "美食", "值得去",
    "哪里有", "有哪些", "吃什么", "玩什么", "好玩吗",
})

GREETING_KEYWORDS: frozenset[str] = frozenset({
    "你好", "嗨", "hello", "hi", "hey",
    "你是谁", "在吗",
})


def _looks_like_trip(text: str) -> bool:
    """Decide whether `text` is actually a trip-planning request.

    Casual mentions of "行程" / "几天" / "路线" are common in small-talk
    ("我今天行程很赶", "请问行程单号多少"), so we require stronger evidence:
    a day count, a trip verb paired with a destination, or an explicit phrase
    from ``_TRIP_PHRASE_PATTERNS``.
    """
    for pattern in _TRIP_PHRASE_PATTERNS:
        if pattern.search(text):
            return True
    # Soft hints alone are not enough — pair them with a clear day cue.
    has_hint = any(hint in text for hint in TRIP_SOFT_HINTS)
    if has_hint and re.search(r"\d+\s*[天日]", text):
        return True
    return False


class RouterNode:
    """Classifies user intent and routes to appropriate downstream node."""

    def _classify_intent(self, text: str) -> str:
        """Classify user input text into an intent category.

        Priority order:
        1. trip_planning — checked first because trip requests may contain
           POI keywords (e.g. "规划行程，推荐好吃的")
        2. poi_recommendation
        3. general — fallback

        Args:
            text: User input text (Chinese or English).

        Returns:
            One of: 'trip_planning', 'poi_recommendation', 'general'.
        """
        if not text:
            return "general"

        text_lower = text.lower()

        # Trip keywords take priority (strong + pattern-based detection).
        if any(kw in text_lower for kw in TRIP_KEYWORDS) or _looks_like_trip(text):
            return "trip_planning"

        # POI recommendation keywords
        if any(kw in text_lower for kw in POI_KEYWORDS):
            return "poi_recommendation"

        # Fallback to general
        return "general"

    def route(self, state: AgentState) -> AgentState:
        """Classify intent from the latest user message and update state.

        Extracts the last user message, classifies it, and returns a
        **new** state dict with the `intent` field set. The original
        state is not mutated.

        Args:
            state: Current agent state.

        Returns:
            New AgentState with 'intent' field populated.
        """
        # Extract the last user message text
        messages = state.get("messages", [])
        last_user_text = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_text = msg.get("content", "")
                break

        intent = self._classify_intent(last_user_text)

        # Return a new state dict (immutable pattern)
        return {**state, "intent": intent}
