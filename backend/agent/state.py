"""AgentState TypedDict for the AI Travel Planner LangGraph workflow.

All fields flowing through the agent graph are defined here.
Nodes read from and return new copies of this state (immutable pattern).
"""

from typing import TypedDict, Any


class AgentState(TypedDict):
    """State dictionary passed between all nodes in the agent graph.

    Fields:
        messages: List of message dicts with 'role' and 'content' keys.
        session_id: Unique identifier for the conversation session.
        intent: Classified intent — 'trip_planning', 'poi_recommendation', or 'general'.
        city: Target city name extracted from user input (None until extracted).
        days: Number of trip days (None until extracted).
        preferences: List of user preference strings (e.g. ['文化', '美食']).
        companion_types: List of companion type strings (e.g. ['情侣', '亲子']).
        budget_level: Budget level 1-5 (None until determined).
        candidate_pois: List of candidate POI dicts from spatial search.
        selected_pois: List of POI dicts selected after scoring/reranking.
        daily_plans: List of daily plan dicts with per-day POI assignments.
        route_polylines: List of route polyline dicts for map visualization.
        recommendation_weights: Dict of weight overrides for scoring pipeline.
        response_text: Final formatted response text for the user.
        structured_plan: Structured plan dict for API serialization.
    """

    # Conversation
    messages: list
    session_id: str
    intent: str

    # Trip parameters
    city: str | None
    days: int | None
    preferences: list[str]
    companion_types: list[str]
    budget_level: int | None

    # POI & planning
    candidate_pois: list
    selected_pois: list
    daily_plans: list
    route_polylines: list

    # Scoring & output
    recommendation_weights: dict[str, Any] | None
    response_text: str
    structured_plan: list[dict[str, Any]] | None
