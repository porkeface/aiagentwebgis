# Task 4.2: POI Service + API

**Files:**
- Create: `backend/app/services/poi_service.py`
- Create: `backend/app/api/v1/poi.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_api/test_poi_api.py`

**Steps:**
1. poi_service.py: search_pois(db, city, category?, keyword?, bbox?, rating_min?, page, size) -> paginated results
2. poi.py API: GET /api/v1/poi/search with query params
3. Response envelope: {success: true, data: {total, items: [...]}}
4. Write API test with mock DB
5. Commit: `feat: POI search API with spatial filtering`
