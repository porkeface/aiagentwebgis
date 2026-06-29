# Task 1.3: Amap API Service — Report

**Status:** DONE

## Summary

Implemented `AmapService` — an async client for the Amap (Gaode) REST API providing POI search, geocoding, reverse geocoding, and route planning capabilities.

## Files Created

### `backend/app/services/__init__.py`
Service layer package init, exports `AmapService`.

### `backend/app/services/amap_service.py`
Core implementation with the following methods:

| Method | API Endpoint | Description |
|--------|-------------|-------------|
| `__init__(api_key)` | — | Stores API key, lazy-creates httpx client |
| `_request(endpoint, params)` | — | Internal GET with auto key injection |
| `search_pois(city, keyword?, category?, limit=20)` | `place/text` | Returns `list[dict]` with lng/lat |
| `geocode(address)` | `geocode/geo` | Returns `(lng, lat)` tuple |
| `reverse_geocode(lng, lat)` | `geocode/regeo` | Returns `{address, city}` dict |
| `plan_route(origin, destination, mode="walking")` | `direction/{mode}` | Returns `{distance_km, duration_min, polyline}` |

**Key design decisions:**
- Lazy httpx.AsyncClient creation via `_get_client()` to avoid resource leaks
- Central `_request()` handles key injection, error checking, and HTTP errors
- Location strings parsed from Amap's `"lng,lat"` format to floats
- Handles Amap's edge case where `city` can be `[]` for direct-administered municipalities
- Route polyline concatenated from all step segments

### `backend/tests/test_amap_service.py`
8 tests using mocked httpx responses:

| Test Class | Tests | Description |
|-----------|-------|-------------|
| `TestSearchPois` | 3 | list parsing, empty handling, param injection |
| `TestGeocode` | 2 | coordinate extraction, empty result error |
| `TestReverseGeocode` | 1 | address/city extraction |
| `TestPlanRoute` | 2 | polyline/distance/duration, driving mode |

## Test Results

```
47 passed in 0.56s  (8 new + 39 existing, zero regressions)
```

## Commit

```
feat: Amap API service - POI search, geocoding, route planning
```

Files: `backend/app/services/__init__.py`, `backend/app/services/amap_service.py`, `backend/tests/test_amap_service.py`
