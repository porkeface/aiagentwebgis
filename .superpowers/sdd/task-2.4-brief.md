# Task 2.4: Formatter Node

**Files:**
- Create: `backend/agent/nodes/formatter.py`
- Modify: `backend/agent/graph.py` (replace placeholder with real FormatterNode)
- Test: `backend/tests/test_agent/test_formatter.py`

**Consumes:** AgentState with planning results
**Produces:** List of SSE event dicts

**Steps:**

1. FormatterNode class with format(state) -> list[dict]:
   - If candidate_pois: emit poi_result event (pois + center + zoom)
   - If daily_plans: emit route_result event (daily_plans + polylines)
   - If city + days: emit plan_summary event
   - Always emit text event with response_text

2. _calc_center(pois): average lng/lat of POIs

3. Update graph.py to use FormatterNode, store events in state["structured_plan"]

4. Write tests:
   - test_formatter_produces_sse_events: verify event list has text
   - test_formatter_includes_poi_result: verify poi_result with correct POI count
   - test_formatter_includes_route_result: verify route_result
   - test_formatter_general_intent_text_only: no poi_result for general intent

5. Run: `pytest tests/test_agent/test_formatter.py -v` -- all 4 pass
6. Commit: `feat: Formatter node - SSE event packaging from AgentState`
