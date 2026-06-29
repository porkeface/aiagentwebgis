# Task 2.4 Report: Formatter Node

**Status:** DONE
**Date:** 2026-06-29

## Summary

Implemented FormatterNode that converts AgentState into a list of SSE (Server-Sent Events) event dicts for frontend streaming.

## Changes

### New Files

1. **backend/agent/nodes/formatter.py**
   - `FormatterNode` class with async `format(state: AgentState) -> dict`
   - `_calc_center(pois)` calculates average lng/lat of POIs (returns Beijing default if empty)
   - Emits events conditionally:
     - `poi_result` when candidate_pois present (includes center + zoom:12)
     - `route_result` when daily_plans present (includes polylines)
     - `plan_summary` when city and days present
     - `text` always emitted with response_text
   - Returns new state dict (immutable pattern)

2. **backend/tests/test_agent/test_formatter.py**
   - 11 comprehensive tests covering all requirements
   - Tests for _calc_center: single POI, multiple POIs, empty list, immutability
   - Tests for format(): text events, poi_result, route_result, plan_summary, general intent text-only, immutability, full trip state

### Modified Files

1. **backend/agent/graph.py**
   - Removed placeholder `formatter_node` function
   - Imported and instantiated `FormatterNode`
   - Replaced placeholder with `formatter_node.format` in graph

2. **backend/tests/test_agent/test_router.py**
   - Fixed `test_graph_routes_general_to_formatter`: changed sync `graph.invoke()` to async `await graph.ainvoke()` because formatter is now async

## Test Results

```
tests/test_agent/test_formatter.py::TestCalcCenter::test_calc_center_single_poi PASSED
tests/test_agent/test_formatter.py::TestCalcCenter::test_calc_center_multiple_pois PASSED
tests/test_agent/test_formatter.py::TestCalcCenter::test_calc_center_empty_list_returns_default PASSED
tests/test_agent/test_formatter.py::TestCalcCenter::test_calc_center_does_not_mutate_input PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_produces_sse_events PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_includes_poi_result PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_includes_route_result PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_includes_plan_summary PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_general_intent_text_only PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_does_not_mutate_state PASSED
tests/test_agent/test_formatter.py::TestFormatterProducesSSEEvents::test_formatter_full_trip_state PASSED

11 new tests PASSED
All 74 agent tests PASSED (no regressions)
```

## Implementation Details

- Followed immutable pattern: all state updates return new dicts
- Handled edge cases: empty POI list returns default center (Beijing: 116.4, 39.9)
- Event order: poi_result → route_result → plan_summary → text
- Used `state.get()` with defaults for safe field access
- Async method compatible with LangGraph's async execution

## Key Design Decisions

1. **Default center for empty POIs**: Beijing (116.4, 39.9) — reasonable fallback for China-focused travel app
2. **Zoom level**: Fixed at 12 for POI results — appropriate city-level view
3. **Event ordering**: Consistent order ensures predictable SSE stream
4. **No mutation**: Original state dict never modified, follows project pattern

## Next Steps

Task 2.4 completes the core agent graph pipeline. The graph now has:
- Router → intent classification
- Planner → LLM-based trip parameter extraction and response generation
- Formatter → SSE event packaging

Ready for Task 3.1: Spatial Filter (POI search and clustering).
