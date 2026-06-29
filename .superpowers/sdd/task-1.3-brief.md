### Task 1.3: Amap API Service

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/amap_service.py`
- Test: `backend/tests/test_amap_service.py`

**Consumes:** config.py (AMAP_API_KEY)
**Produces:** AmapService class with search_pois(), geocode(), reverse_geocode(), plan_route()

**Steps:**

1. Write tests first (mock httpx responses):
   - test_search_pois_returns_list: mock response with 1 POI, verify parsing
   - test_geocode_returns_coordinates: mock geocode response, verify (lng, lat) tuple
   - test_plan_route_returns_polyline: mock route response, verify distance_km, duration_min, polyline
   - test_search_pois_handles_empty: mock empty response, verify returns []

2. Create AmapService:
   - `__init__(api_key)`: store key
   - `_request(endpoint, params)`: internal httpx GET with key injection
   - `search_pois(city, keyword?, category?, limit=20)`: GET place/text, parse pois to list of dicts with lng/lat
   - `geocode(address)`: GET geocode/geo, return (lng, lat)
   - `reverse_geocode(lng, lat)`: GET geocode/regeo, return {address, city}
   - `plan_route(origin, destination, mode="walking")`: GET direction/{mode}, return {distance_km, duration_min, polyline}

3. Run: `pytest tests/test_amap_service.py -v` -- all 4 pass
4. Commit: `feat: Amap API service - POI search, geocoding, route planning`

---