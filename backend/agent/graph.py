"""LangGraph StateGraph definition for the AI Travel Planner agent.

Graph structure:
    START -> router -+-> planner (placeholder) -> formatter (placeholder) -> END
                     +--> formatter (placeholder) -> END

The router classifies intent and conditionally routes:
- 'trip_planning' / 'poi_recommendation' -> planner
- 'general' -> formatter (direct response)

Planner and formatter are placeholders for Tasks 2.3 and 2.4.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from agent.state import AgentState
from agent.nodes.router import RouterNode
from agent.nodes.planner import PlannerNode
from agent.llm.factory import get_llm_adapter


# ---------------------------------------------------------------------------
# Placeholder nodes (to be implemented in Task 2.4)
# ---------------------------------------------------------------------------


def formatter_node(state: AgentState) -> AgentState:
    """Placeholder formatter node. Returns state unchanged."""
    return state


# ---------------------------------------------------------------------------
# Router decision function for conditional edges
# ---------------------------------------------------------------------------


def route_after_router(state: AgentState) -> str:
    """Determine which node to visit after the router.

    Args:
        state: Agent state with 'intent' already set by RouterNode.

    Returns:
        Name of the next node: 'planner' or 'formatter'.
    """
    intent = state.get("intent", "general")
    if intent in ("trip_planning", "poi_recommendation"):
        return "planner"
    return "formatter"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph() -> CompiledStateGraph:
    """Build and compile the agent LangGraph.

    Returns:
        A compiled LangGraph ready to be invoked.
    """
    router_node = RouterNode()
    planner_node = PlannerNode(llm_adapter=get_llm_adapter())

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node.route)
    graph.add_node("planner", planner_node.plan)
    graph.add_node("formatter", formatter_node)

    # Edges
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {"planner": "planner", "formatter": "formatter"},
    )
    graph.add_edge("planner", "formatter")
    graph.add_edge("formatter", END)

    return graph.compile()
