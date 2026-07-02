"""AgentState TypedDict for the ReAct agent.

Minimal schema — the agent loop stores everything in `messages`.
`create_react_agent` requires `messages: Annotated[list, add_messages]`.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """State for the ReAct travel agent.

    Required fields (always present):
        messages: Conversation history with tool calls and results,
            auto-reduced via add_messages.
        session_id: Unique session identifier (passed as thread_id).
        tool_call_count: Number of tool invocations so far.

    Optional fields (populated by intent router / planning pipeline):
        error: Error message captured during tool execution.
        intent: Intent type from classifier ("chat"/"poi_query"/"route_query"/"trip_planning").
        intent_city: City extracted from user message.
        intent_days: Number of days extracted from user message.
        intent_preferences: User preference tags.
        plan_result: Final trip plan from planning pipeline.
        plan_city: City from the accepted plan.
        plan_days: Days from the accepted plan.
    """

    messages: Annotated[list, add_messages]
    session_id: str
    tool_call_count: int
    error: str | None
    intent: str
    intent_city: str | None
    intent_days: int | None
    intent_preferences: list[str]
    plan_result: dict
    plan_city: str
    plan_days: int
