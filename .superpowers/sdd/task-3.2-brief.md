# Task 3.2: Multi-Factor Scoring

**Files:**
- Create: `backend/recommendation/scoring.py`
- Test: `backend/tests/test_recommendation/test_scoring.py`

**Consumes:** list[dict] POIs, weights dict, user preferences, center coordinates
**Produces:** scored + sorted POI list with "score" field

**Steps:**

1. Implement score_pois(pois, preferences, weights, center_lng, center_lat):
   - preference_score: Jaccard similarity (POI tags vs user preferences)
   - distance_score: 1.0 - haversine_km / 20.0 (capped at 0)
   - rating_score: rating / 5.0
   - time_score: 0.8 default (opening hours check)
   - popularity_score: review_count / max_review_count
   - total = weighted sum

2. Write tests:
   - test_scoring_prefers_matching_tags
   - test_scoring_prefers_closer_pois
   - test_scoring_prefers_higher_rated
   - test_scoring_sorts_descending

3. Run tests, commit: `feat: multi-factor scoring with Jaccard, distance, rating, popularity`
