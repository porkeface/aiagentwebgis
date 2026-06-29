# Task 3.2: Multi-Factor Scoring — Report

## Status: DONE

**Commit SHA:** `7e3f41ce2bc7357dad2efc1d8fb6ceaaad872c9d`

**Commit Message:** `feat: multi-factor scoring with Jaccard, distance, rating, popularity`

---

## Implementation Summary

### Created: `backend/recommendation/scoring.py`

Pure function implementing multi-factor weighted POI scoring:

- `score_pois(pois, preferences, weights, center_lng, center_lat)` — returns a new sorted list of POI dicts with `"score"` field added (immutable; originals not mutated)
- Five scoring factors, each normalized to `[0, 1]`:
  - `preference_score`: Jaccard similarity (`|intersection| / |union|`); both empty → 0.0
  - `distance_score`: `max(0.0, 1.0 - haversine/20.0)`; no center → 0.5 (neutral)
  - `rating_score`: `min(rating / 5.0, 1.0)`; None → 0.0
  - `time_score`: `0.8` (default placeholder for opening hours)
  - `popularity_score`: `review_count / max_review_count`; max==0 → 0.0
- Total: `sum(weights[factor] * factor_score)`
- Haversine formula implemented using standard WGS84 math (R=6371km)

### Created: `backend/tests/test_recommendation/test_scoring.py`

12 test cases covering:

| Test | Description |
|------|-------------|
| `test_scoring_prefers_matching_tags` | POI with matching tags scores higher |
| `test_scoring_prefers_closer_pois` | Closer POI scores higher on distance |
| `test_scoring_prefers_higher_rated` | Higher rating POI scores higher |
| `test_scoring_sorts_descending` | Result list sorted by score descending |
| `test_returns_new_dicts` | Original POI dicts not mutated |
| `test_empty_pois_returns_empty` | Empty input → empty list |
| `test_none_rating_scores_zero_for_rating` | None rating → rating_score=0.0 |
| `test_no_center_gives_neutral_distance` | No center → distance_score=0.5 |
| `test_both_empty_prefs_and_tags_gives_zero_preference` | Both empty sets → 0.0 |
| `test_popularity_normalization` | Correct popularity scaling |
| `test_distance_beyond_20km_clamps_to_zero` | >20km distance clamps to 0.0 |
| `test_time_score_is_0_8` | Time score defaults to 0.8 |

---

## Test Results

```
12 passed in 0.47s (scoring tests)
145 passed in 1.38s (full suite — no regressions)
```

---

## Design Notes

- **Separation from `agent/tools/spatial_analysis.py`**: The recommendation scoring module (`recommendation/scoring.py`) is the canonical scoring engine for the recommendation pipeline. `score_pois_tool` in `agent/tools/spatial_analysis.py` is the agent-tool wrapper (different normalization for distance, different time_score placeholder at 1.0). No coupling between the two.
- **Immutable pattern**: Uses dict unpacking (`{**poi, "score": total}`) to create new dicts, never mutating originals.
- **Graceful None handling**: Missing/None rating → 0.0, missing center → 0.5 neutral distance, zero review counts → 0.0 popularity.
- **Weights as parameter**: Weights are caller-supplied rather than hardcoded constants, enabling pipeline experimentation without modifying this module.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/recommendation/scoring.py` | Created (118 lines) |
| `backend/tests/test_recommendation/test_scoring.py` | Created (183 lines) |

---

## Task 3.2 Acceptance Criteria Met

- [x] `score_pois` returns new list of POI dicts with `"score"` field
- [x] Sorted descending by score
- [x] All 5 factors implemented per spec
- [x] Haversine formula implemented
- [x] Immutable (originals not mutated)
- [x] 4 required tests pass + 8 additional edge-case tests
- [x] 145/145 total tests pass (no regressions)
- [x] Committed with conventional commit message
