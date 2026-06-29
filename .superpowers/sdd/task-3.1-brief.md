# Task 3.1: Spatial Filter

**Files:**
- Create: `backend/recommendation/__init__.py`, `backend/recommendation/spatial_filter.py`
- Test: `backend/tests/test_recommendation/test_spatial_filter.py`

**Consumes:** database.py, models/poi.py (POI model)
**Produces:** spatial_filter_pois(city, center_lng, center_lat, radius_km) -> list[POI]

**Steps:**

1. Write spatial filter using SQLAlchemy + GeoAlchemy2:
   - ST_DWithin(location, func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326), radius_degrees)
   - Fallback: if local results < min_count, return flag for Amap API supplement
   - radius_degrees = radius_km / 111.0 (approximate)

2. Write tests:
   - test_spatial_filter_returns_pois_within_radius
   - test_spatial_filter_excludes_pois_outside_radius
   - test_spatial_filter_empty_city_returns_empty

3. Run tests, commit: `feat: spatial filter - PostGIS ST_DWithin query`
