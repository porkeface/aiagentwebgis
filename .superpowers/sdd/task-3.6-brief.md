# Task 3.6: Recommendation Pipeline

**Files:**
- Create: `backend/recommendation/pipeline.py`
- Test: `backend/tests/test_recommendation/test_pipeline.py`

**Consumes:** All 5 steps above
**Produces:** run_recommendation_pipeline(city, preferences, days, weights, center) -> full plan

**Steps:**

1. Implement run_recommendation_pipeline():
   - Step 1: spatial_filter_pois() -> ~50 candidates
   - Step 2: score_pois() -> ~20 scored
   - Step 3: mmr_rerank() -> ~12 diverse
   - Step 4: cluster_pois_for_days() -> daily assignments
   - Step 5: optimize_daily_route() per day -> final routes

2. Write integration test:
   - test_full_pipeline_produces_daily_plans: mock spatial filter, verify pipeline structure
   - test_pipeline_returns_correct_number_of_days

3. Run tests, commit: `feat: recommendation pipeline - 5-step orchestration`
