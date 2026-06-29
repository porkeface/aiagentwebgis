# Task 2.3 Report: Planner Agent (ReAct)

老大，Task 2.3 已完成。

## Status: DONE

**Commit SHA:** `f00583aaaa4487c5b65fe9dd5d3f199c7c110517`

## Summary

Implemented the PlannerNode — the core ReAct-style planning agent that extracts trip parameters from user messages, sets recommendation weights based on companion types, calls the LLM, and stores the response.

## Files Created

- `backend/agent/nodes/planner.py` — PlannerNode class (157 lines)
- `backend/tests/test_agent/test_planner.py` — 13 tests (186 lines)

## Files Modified

- `backend/agent/graph.py` — Replaced placeholder planner with real PlannerNode wired via `get_llm_adapter()`
- `backend/tests/test_agent/test_router.py` — Updated integration test to use `async def` + `ainvoke` + mock LLM adapter (planner is now async)

## Implementation Details

### PlannerNode (`backend/agent/nodes/planner.py`)

| Method | Purpose |
|--------|---------|
| `__init__(llm_adapter)` | Stores BaseLLMAdapter instance |
| `async plan(state)` | Main entry: extract params → ensure weights → build messages → call LLM → set response_text |
| `_extract_params(state)` | Returns `{city, days}` from last user message via regex |
| `_extract_city(text)` | Matches `X市` pattern then known cities (北京/上海/杭州/etc.) |
| `_extract_days(text)` | Handles Arabic (`3天`), Chinese (`两天`/`三日`), and `一日游` |
| `_ensure_weights(state)` | Sets default weights if `recommendation_weights is None` |
| `_default_weights(companion_types)` | Adjusts weights for elderly/children companions |
| `_build_messages(state)` | Prepends SYSTEM_PROMPT to conversation history |

### SYSTEM_PROMPT

Chinese travel planning assistant prompt covering:
- Generate reasonable itineraries based on city/days
- Consider geographic proximity to avoid backtracking
- Recommend local food and restaurants
- Account for companion types (elderly, children, couples)
- Default to 2-day trip when unspecified
- Include transport and budget advice

### Weight Logic

| Companion | Key Weight Changes |
|-----------|-------------------|
| Default | preference=0.30, distance=0.20, rating=0.20, time=0.15, popularity=0.15 |
| elderly | distance_weight=0.15, time_weight=0.25 (less walking, more rest time) |
| children | distance_weight=0.15, popularity_weight=0.20 (kid-friendly popular spots) |

## Test Summary

**63/63 agent tests pass** (13 new planner tests + 50 existing)

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestPlannerResponse | 2 | response_text set, immutability |
| TestPlannerExtraction | 6 | city/days from Chinese/Arabic, known cities, multi-message |
| TestPlannerWeights | 5 | defaults, sum≈1.0, elderly, children, no overwrite |
| TestBuildGraph (updated) | 1 | async ainvoke with mock adapter verifies full pipeline |

## Graph Integration

`build_graph()` now instantiates `PlannerNode(llm_adapter=get_llm_adapter())` — the planner is a real async node that calls the configured LLM provider. The existing `route_after_router` conditional edge logic is unchanged; trip_planning/poi_recommendation intents still route to planner.
