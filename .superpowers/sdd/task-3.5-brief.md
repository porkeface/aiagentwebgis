# Task 3.5: TSP Route Optimization

**Files:**
- Create: `backend/recommendation/tsp.py`
- Test: `backend/tests/test_recommendation/test_tsp.py`

**Consumes:** daily POI list
**Produces:** optimized visiting order + total distance

**Steps:**

1. Implement optimize_daily_route(pois):
   - Build distance matrix using haversine
   - Nearest neighbor heuristic starting from POI closest to city center
   - 2-opt improvement: iterate swaps until no improvement
   - Return ordered POI list + per-segment distances

2. Write tests:
   - test_tsp_reduces_total_distance_vs_input_order
   - test_tsp_preserves_all_pois
   - test_tsp_single_poi_returns_same

3. Run tests, commit: `feat: TSP optimization - nearest neighbor + 2-opt improvement`
