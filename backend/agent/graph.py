"""LangGraph StateGraph definition for the AI Travel Planner agent.

Graph structure:
    START -> router -> planner -> formatter -> END

The router classifies intent (trip_planning / poi_recommendation / general).
All intents then flow through the planner, which:
  - For trip_planning / poi_recommendation: extracts city/days, calls
    Amap tools, scores POIs, builds daily plans.
  - For general (chitchat / capability questions): skips the tools and
    delegates the response entirely to the LLM with a chat-style system
    prompt. This way the "dialog" feels real instead of returning an
    empty text event when the user just says "你好".
The formatter then packages all SSE events for the client.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from agent.state import AgentState
from agent.nodes.router import RouterNode
from agent.nodes.planner import PlannerNode
from agent.nodes.formatter import FormatterNode
from agent.llm.factory import get_llm_adapter
from agent.checkpointer import get_checkpointer


# ---------------------------------------------------------------------------
# Module-level cache for compiled graph
# ---------------------------------------------------------------------------

_compiled_graph: CompiledStateGraph | None = None


# ---------------------------------------------------------------------------
# Routing helper
# ---------------------------------------------------------------------------

# All intents flow through the planner. The planner itself decides whether
# to call tools (only for trip_planning / poi_recommendation) or skip straight
# to the LLM (for general). Routing everything through planner keeps a single
# state-mutation surface and avoids the "empty response" footgun where the
# formatter has no text to emit because the LLM was bypassed entirely.
_PLANNING_INTENTS = {"trip_planning", "poi_recommendation", "general"}


def _route_after_router(state: AgentState) -> str:
    """All routed intents go through the planner; planner decides tool use."""
    intent = (state.get("intent") or "").strip()
    return "planner" if intent in _PLANNING_INTENTS else "formatter"


def reset_compiled_graph() -> None:
    """Drop the cached compiled graph (used by tests / config hot-reload)."""
    global _compiled_graph
    _compiled_graph = None


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(checkpointer: object | None = None) -> CompiledStateGraph:
    """Build and compile the agent LangGraph.

    Args:
        checkpointer: Optional checkpointer override.
            - Default (None): use the process-wide ``get_checkpointer()`` and
              cache the compiled graph for subsequent callers.
            - ``False``: skip checkpointer entirely (useful for tests that
              don't supply a ``thread_id``). Result is NOT cached.
            - ``BaseCheckpointSaver``: use the supplied checkpointer. Result is
              NOT cached.

    Returns:
        A compiled LangGraph ready to be invoked.
    """
    global _compiled_graph
    # Use the cached graph only when the caller didn't explicitly opt out
    # (passed anything other than the default).
    use_default = checkpointer is None
    if use_default and _compiled_graph is not None:
        return _compiled_graph

    router_node = RouterNode()
    planner_node = PlannerNode(llm_adapter=get_llm_adapter())
    formatter_node = FormatterNode()

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node.route)
    graph.add_node("planner", planner_node.plan)
    graph.add_node("formatter", formatter_node.format)

    # Edges
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {"planner": "planner", "formatter": "formatter"},
    )
    graph.add_edge("planner", "formatter")
    graph.add_edge("formatter", END)

    if use_default:
        cp = get_checkpointer()
        # A falsy checkpointer (None / False) tells langgraph "don't persist".
        # We treat falsy the same as `False` so dev setups without Redis/PG
        # still work without forcing thread_id on every request.
        effective_cp = cp if cp else False
        compiled = graph.compile(checkpointer=effective_cp)
        _compiled_graph = compiled
        return compiled

    # Explicit path: ``False`` = no checkpointer, anything else = provided one.
    effective_cp = checkpointer if checkpointer else False
    return graph.compile(checkpointer=effective_cp)
