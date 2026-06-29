# Task 2.2 Report: Agent Tool Chain

**Status:** DONE
**Commit:** `267d82a`
**Branch:** `ai-travel-planner`

## Summary

Implemented 7 async tool functions wrapping `AmapService` for the LangGraph agent, plus a singleton factory and `ALL_TOOLS` export list.

## Files Created

| File | Purpose |
|------|---------|
| `backend/agent/tools/__init__.py` | Package init: `get_amap()` singleton, `ALL_TOOLS` list, re-exports |
| `backend/agent/tools/poi_search.py` | `search_pois_tool`, `search_nearby_tool` |
| `backend/agent/tools/geocoding.py` | `geocode_tool`, `reverse_geocode_tool` |
| `backend/agent/tools/route_planning.py` | `plan_route_tool` |
| `backend/agent/tools/spatial_analysis.py` | `score_pois_tool` (pure computation, multi-factor scoring) |
| `backend/agent/tools/weather.py` | `get_weather_tool` (MVP placeholder) |
| `backend/tests/test_agent/test_tools.py` | 21 tests covering all tools |

## Design Decisions

### Singleton Pattern
`get_amap()` creates a single `AmapService` instance lazily, reading `AMAP_API_KEY` from env. `_reset_amap_instance()` exposed for test cleanup.

### Lazy Imports
Tool functions import `get_amap` inside the function body (not at module level) to avoid circular imports between `__init__.py` and sub-modules.

### Multi-Factor Scoring (`score_pois_tool`)
- **preference_score** (w=0.30): Jaccard similarity between POI tags ∩ user preferences
- **distance_score** (w=0.20): `1 - haversine_dist / max_dist` from city center
- **rating_score** (w=0.20): `rating / 5.0` capped at 1.0
- **time_score** (w=0.15): placeholder = 1.0 for MVP
- **popularity_score** (w=0.15): `review_count / max_review_count`
- All individual scores normalized to [0, 1]
- `_compute_scores()` is a pure helper returning per-factor breakdown (testable)

### Weather Placeholder
Returns `{"city", "temperature": 25, "condition": "晴", "humidity": 60}` — to be replaced with real API in a future task.

## Test Summary

```
21 passed in 0.18s
103 total tests pass (no regressions)
```

### Test Classes:
- `TestSearchPoisTool` (3 tests): service calls, empty results, nearby search
- `TestGeocodeTool` (3 tests): forward/reverse geocoding
- `TestPlanRouteTool` (2 tests): route with default/walking mode
- `TestScorePoisTool` (7 tests): scoring output, Jaccard ordering, weights sum, normalization, empty input
- `TestGetWeatherTool` (2 tests): placeholder structure, city parameter
- `TestGetAmap` (2 tests): singleton identity, instance type
- `TestAllTools` (2 tests): name set completeness, callability

## Key Implementation Detail
`search_nearby_tool` calls `amap.search_nearby()` which is not yet on `AmapService`. This will be added when the place/around endpoint is implemented. Tests mock this method on the `MagicMock` directly.
