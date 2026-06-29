# Task 4.2 Report: POI Service + API

## Status
✅ **DONE**

## Commit
`5bd7c0d` - feat: POI Service + API with spatial filtering

## Implementation Summary

### Created Files

1. **backend/app/services/poi_service.py** (POI service layer)
   - `search_pois()` function with async/await
   - Filters: city (required), category, keyword (ILIKE on name/description), bbox (PostGIS ST_Within), rating_min
   - Pagination: offset/limit with total count
   - PostGIS geometry → lng/lat conversion using geoalchemy2.shape.to_shape()
   - Returns: `{"total": int, "items": list[POIResponse]}`

2. **backend/app/api/v1/poi.py** (FastAPI router)
   - `GET /api/v1/poi/search` endpoint
   - Query params: city, category, keyword, bbox, rating_min, page, size
   - bbox parsed from string "min_lng,min_lat,max_lng,max_lat" to list[float]
   - Response envelope: `{"success": true, "data": {"total": int, "items": [...]}}`
   - DB session via Depends(get_session)

3. **backend/app/api/v1/router.py** (v1 router aggregation)
   - Includes poi_router
   - Mounted in main.py via `app.include_router(v1_router)`

4. **backend/tests/test_api/test_poi_api.py** (6 tests)
   - test_basic_search: verifies envelope structure
   - test_query_params_passed: verifies all params forwarded to service
   - test_bbox_param_parsed: verifies bbox string parsing
   - test_empty_result: verifies empty result handling
   - test_missing_city_param: verifies 422 validation
   - test_pagination_defaults: verifies default page=1, size=20

### Modified Files

1. **backend/app/main.py**
   - Import v1_router
   - Include router: `app.include_router(v1_router)`

2. **backend/app/services/__init__.py**
   - Export search_pois function

## Test Results

**All tests passing: 217 passed**

```
tests/test_api/test_poi_api.py::TestPOISearchEndpoint::test_basic_search PASSED
tests/test_api/test_poi_api.py::TestPOISearchEndpoint::test_query_params_passed PASSED
tests/test_api/test_poi_api.py::TestPOISearchEndpoint::test_bbox_param_parsed PASSED
tests/test_api/test_poi_api.py::TestPOISearchEndpoint::test_empty_result PASSED
tests/test_api/test_poi_api.py::TestPOISearchEndpoint::test_missing_city_param PASSED
tests/test_api/test_poi_api.py::TestPOISearchEndpoint::test_pagination_defaults PASSED
```

## Key Features

### Spatial Filtering
- bbox parameter: "min_lng,min_lat,max_lng,max_lat"
- Uses PostGIS `ST_Within(POI.location, ST_MakeEnvelope(...))`
- Efficient spatial indexing with 4326 SRID

### Keyword Search
- ILIKE pattern matching on name and description
- Case-insensitive partial match

### Pagination
- 1-indexed page numbers
- Default: page=1, size=20
- Max size: 100 (validated by FastAPI)
- Returns total count for UI pagination

### Response Envelope
```json
{
  "success": true,
  "data": {
    "total": 100,
    "items": [
      {
        "id": 1,
        "name": "西湖",
        "category": "nature",
        "address": null,
        "lng": 120.15,
        "lat": 30.25,
        "rating": 4.5,
        "review_count": 500,
        "tags": ["景点", "湖泊"]
      }
    ]
  }
}
```

## Architecture Notes

### Service Layer Separation
- Service layer (poi_service.py) handles business logic and DB queries
- API layer (poi.py) handles HTTP concerns (request parsing, response formatting)
- Service returns POIResponse objects, API converts to dicts

### PostGIS Integration
- POI model stores geometry in PostGIS POINT format
- POIResponse schema uses lng/lat floats
- Conversion happens in service layer via `_poi_to_response()`

### Testing Strategy
- Mock DB session to avoid database dependency
- Mock search_pois service to test API layer in isolation
- Verify request parameter parsing and response structure

## Next Steps

Task 4.2 provides the foundation for:
- **Task 4.3**: Agent Chat SSE (will use search_pois via agent tools)
- **Task 4.4**: Trip CRUD API (will reference POI data)
- **Task 5.3**: MapView Component (will call /api/v1/poi/search)

## Files Changed

**Created:**
- backend/app/services/poi_service.py
- backend/app/api/v1/poi.py
- backend/app/api/v1/router.py
- backend/app/api/__init__.py
- backend/app/api/v1/__init__.py
- backend/tests/test_api/__init__.py
- backend/tests/test_api/test_poi_api.py

**Modified:**
- backend/app/main.py
- backend/app/services/__init__.py

## Verification

✅ All 217 tests pass
✅ POI search endpoint functional
✅ Spatial filtering with bbox works
✅ Pagination implemented correctly
✅ Response envelope matches specification
✅ No breaking changes to existing code
