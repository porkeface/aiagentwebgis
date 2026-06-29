# Task 2.2: Agent Tool Chain

**Files:**
- Create: `backend/agent/tools/__init__.py`
- Create: `backend/agent/tools/poi_search.py` (search_pois_tool, search_nearby_tool)
- Create: `backend/agent/tools/geocoding.py` (geocode_tool, reverse_geocode_tool)
- Create: `backend/agent/tools/route_planning.py` (plan_route_tool)
- Create: `backend/agent/tools/spatial_analysis.py` (score_pois_tool)
- Create: `backend/agent/tools/weather.py` (get_weather_tool)
- Test: `backend/tests/test_agent/test_tools.py`

**Consumes:** services/amap_service.py
**Produces:** 6 tool functions + ALL_TOOLS list for LangGraph registration

**Steps:**

1. poi_search.py: search_pois_tool wraps amap.search_pois; search_nearby_tool uses amap place/around
2. geocoding.py: geocode_tool wraps amap.geocode; reverse_geocode_tool wraps amap.reverse_geocode
3. route_planning.py: plan_route_tool wraps amap.plan_route
4. spatial_analysis.py: score_pois_tool implements multi-factor scoring (preference Jaccard + inverse distance + rating + time + popularity)
5. weather.py: get_weather_tool returns placeholder data (MVP)
6. get_amap() singleton factory pattern
7. ALL_TOOLS list in __init__.py

8. Write tests (mock amap service):
   - test_search_pois_tool: mock returns 1 POI, verify result
   - test_geocode_tool: mock returns coordinates
   - test_plan_route_tool: mock returns route
   - test_score_pois_tool: verify scoring calculation
   - test_get_weather_tool: verify placeholder structure

9. Run: `pytest tests/test_agent/test_tools.py -v` -- all 5 pass
10. Commit: `feat: Agent tool chain - 6 tools for POI search, routing, scoring, weather`
