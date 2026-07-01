"""AgentState TypedDict for the ReAct agent.

Minimal schema — the agent loop stores everything in `messages`.
`create_react_agent` requires `messages: Annotated[list, add_messages]`.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the ReAct travel agent.

    Fields:
        messages: Conversation history with tool calls and results,
            auto-reduced via add_messages.
        session_id: Unique session identifier (passed as thread_id).
        tool_call_count: Number of tool invocations so far — only
            counts actual tool calls, not LLM thinking rounds.
        error: Error message captured during tool execution (None = no error).
    """

    messages: Annotated[list, add_messages]
    session_id: str
    tool_call_count: int
    error: str | None
