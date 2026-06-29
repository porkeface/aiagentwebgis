# Task 2.3: Planner Agent (ReAct)

**Files:**
- Create: `backend/agent/nodes/planner.py`
- Modify: `backend/agent/graph.py` (replace placeholder with real PlannerNode)
- Test: `backend/tests/test_agent/test_planner.py`

**Consumes:** agent/llm (BaseLLMAdapter), agent/tools, agent/state
**Produces:** PlannerNode that extracts params, calls LLM, updates state

**Steps:**

1. Define SYSTEM_PROMPT for travel planning assistant
2. Define regex patterns for city/days extraction from text
3. PlannerNode class:
   - __init__(llm_adapter)
   - plan(state) -> state: extract params, ensure weights, build messages, call LLM, set response_text
   - _extract_params(state): regex extract city and days from last user message
   - _ensure_weights(state): set default weights based on companion_types

4. Update graph.py to use PlannerNode instead of placeholder
5. Write tests:
   - test_planner_produces_response_text: mock LLM, verify response_text is set
   - test_planner_extracts_city_from_message: verify city extraction
   - test_planner_sets_default_weights: verify weights are populated

6. Run: `pytest tests/test_agent/test_planner.py -v` -- all 3 pass
7. Commit: `feat: Planner Agent node with ReAct pattern and parameter extraction`
