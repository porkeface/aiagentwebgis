# Task 2.1: LangGraph StateGraph + Router

**Files:**
- Create: `backend/agent/state.py` (AgentState TypedDict)
- Create: `backend/agent/graph.py` (build_graph() -> compiled StateGraph)
- Create: `backend/agent/nodes/__init__.py`, `backend/agent/nodes/router.py`
- Test: `backend/tests/test_agent/test_router.py`

**Consumes:** agent/llm (for future LLM-based intent classification)
**Produces:** AgentState type, compiled LangGraph with router->planner/formatter routing

**Steps:**

1. Define AgentState TypedDict with all fields: messages, session_id, intent, city, days, preferences, companion_types, budget_level, candidate_pois, selected_pois, daily_plans, route_polylines, recommendation_weights, response_text, structured_plan

2. Create RouterNode:
   - Keyword-based intent classification (MVP): TRIP_KEYWORDS, POI_KEYWORDS, GREETING_KEYWORDS
   - _classify_intent(text) -> "trip_planning" | "poi_recommendation" | "general"
   - route(state) -> updated state with intent set

3. Create build_graph():
   - StateGraph(AgentState) with 3 nodes: router, planner, formatter
   - START -> router -> conditional_edges(trip_planning/poi_recommendation -> planner, general -> formatter)
   - planner -> formatter -> END
   - planner/formatter are placeholders (Tasks 2.3, 2.4)

4. Write tests:
   - test_router_classifies_trip_planning: "帮我规划杭州两日游" -> trip_planning
   - test_router_classifies_poi_recommendation: "杭州有什么好吃的" -> poi_recommendation
   - test_router_classifies_general: "你好" -> general
   - test_agent_state_has_required_fields

5. Run: `pytest tests/test_agent/test_router.py -v` -- all 4 pass
6. Commit: `feat: LangGraph StateGraph with Router node and conditional routing`
