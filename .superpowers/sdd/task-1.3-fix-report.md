# Task 1.3 Review Fix Report

**Date:** 2026-06-29
**Task:** Amap API Service (backend/app/services/amap_service.py)

---

## Issues Fixed

### H1: plan_route mode parameter path injection ✅
- Added `VALID_ROUTE_MODES` frozenset whitelist: `{"walking", "driving", "bicycling", "transit"}`
- Validation occurs at the top of `plan_route` before the mode is interpolated into the URL path
- Invalid modes raise `ValueError` with a clear message listing valid options

### H2: Missing async context manager ✅
- Implemented `__aenter__` returning `self`
- Implemented `__aexit__` calling `await self.close()` and returning `False` (does not suppress exceptions)
- Enables `async with AmapService(api_key) as svc:` pattern

### H3: geocode lacks exception handling for coordinate parsing ✅
- Replaced manual pre-checks with a `try/except` block around `geocodes[0]["location"].split(",")`
- Catches `KeyError`, `IndexError`, and `ValueError`
- Re-raises as `ValueError` with the original exception chained via `from e`

### H4: Error path tests missing ✅
Added 6 new tests across 2 new test classes:

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | `test_plan_route_invalid_mode_raises` | Invalid mode raises `ValueError` before API call |
| 2 | `test_api_business_error_raises` | API `status != "1"` raises `ValueError` with info message |
| 3 | `test_http_non_200_raises` | HTTP 500 triggers `httpx.HTTPStatusError` via `raise_for_status` |
| 4 | `test_reverse_geocode_municipality_city_is_list` | `city=[]` (municipality) falls back to `province` |
| 5 | `test_geocode_parse_error_raises` | Malformed location string raises `ValueError` with cause |
| 6 | `test_async_context_manager` | `async with` closes client on exit |

---

## Test Summary

```
tests/test_amap_service.py::TestSearchPois::test_search_pois_returns_list         PASSED
tests/test_amap_service.py::TestSearchPois::test_search_pois_handles_empty        PASSED
tests/test_amap_service.py::TestSearchPois::test_search_pois_injects_key_and_params PASSED
tests/test_amap_service.py::TestGeocode::test_geocode_returns_coordinates           PASSED
tests/test_amap_service.py::TestGeocode::test_geocode_empty_result_raises           PASSED
tests/test_amap_service.py::TestReverseGeocode::test_reverse_geocode_returns_address PASSED
tests/test_amap_service.py::TestPlanRoute::test_plan_route_returns_polyline          PASSED
tests/test_amap_service.py::TestPlanRoute::test_plan_route_driving_mode              PASSED
tests/test_amap_service.py::TestPlanRoute::test_plan_route_invalid_mode_raises       PASSED  ← NEW
tests/test_amap_service.py::TestErrorPaths::test_api_business_error_raises           PASSED  ← NEW
tests/test_amap_service.py::TestErrorPaths::test_http_non_200_raises                 PASSED  ← NEW
tests/test_amap_service.py::TestErrorPaths::test_reverse_geocode_municipality_city_is_list PASSED ← NEW
tests/test_amap_service.py::TestErrorPaths::test_geocode_parse_error_raises          PASSED  ← NEW
tests/test_amap_service.py::TestContextManager::test_async_context_manager           PASSED  ← NEW

14 passed in 0.13s
```

**Old tests:** 8 (all still pass)
**New tests:** 6 (all pass)
**Total:** 14/14 passing

---

## Commit

- **SHA:** `519c368`
- **Message:** `fix: amap service - mode validation, context manager, error handling, tests`
- **Files changed:** 2
  - `backend/app/services/amap_service.py` (+36/-8 lines)
  - `backend/tests/test_amap_service.py` (+126/-0 lines)
