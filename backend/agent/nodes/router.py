"""Router Node for intent classification.

Classifies user messages into one of three intents:
- 'trip_planning': User wants to plan a trip/itinerary
- 'poi_recommendation': User asks for POI recommendations (food, sights, etc.)
- 'general': Greetings or general chat

This is the MVP keyword-based implementation. Future iterations may use
LLM-based classification for higher accuracy.
"""

from agent.state import AgentState


# Keyword sets for intent classification
TRIP_KEYWORDS: frozenset[str] = frozenset({
    "规划", "旅行", "旅游", "行程", "日游", "行程安排",
    "计划", "几天", "攻略路线", "路线规划",
})

POI_KEYWORDS: frozenset[str] = frozenset({
    "推荐", "好吃", "好玩", "景点", "美食", "值得去",
    "哪里有", "有哪些", "吃什么", "玩什么", "好玩吗",
})

GREETING_KEYWORDS: frozenset[str] = frozenset({
    "你好", "嗨", "hello", "hi", "hey",
    "你是谁", "在吗",
})


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

        # Trip keywords take priority
        if any(kw in text for kw in TRIP_KEYWORDS):
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
