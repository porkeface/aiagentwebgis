# Task 3.3: MMR Diversity Rerank — Report

**Status:** DONE
**Commit:** `29b08a0`
**Date:** 2026-06-29

## Summary

Implemented Maximal Marginal Relevance (MMR) algorithm for diversity-aware POI selection. The algorithm balances relevance (score from scoring.py) against category diversity (Jaccard similarity of tags) to produce more interesting recommendation lists.

## Files Created

- `backend/recommendation/mmr.py` — MMR reranking implementation
- `backend/tests/test_recommendation/test_mmr.py` — Comprehensive test suite

## Implementation Details

### `similarity(poi_a, poi_b) -> float`
- Computes Jaccard overlap: `|tags_a ∩ tags_b| / |tags_a ∪ tags_b|`
- Returns 0.0 when both POIs have empty/missing tags
- Handles missing "tags" field gracefully via `poi.get("tags", [])`

### `mmr_rerank(pois, lambda_=0.7, k=10) -> list[dict]`
- Iteratively selects POI maximizing: `mmr = lambda * relevance - (1 - lambda) * max_similarity_to_selected`
- `relevance` = POI's "score" field
- `max_similarity_to_selected` = 0.0 for first pick, max Jaccard to any selected POI thereafter
- Returns original POI dict references (not copies) in selection order
- Handles edge cases: empty list, k > len(pois), k=0

## Test Results

**All 15 MMR tests passed:**

Similarity tests (6):
- `test_identical_tags` — Same tags → 1.0
- `test_disjoint_tags` — No overlap → 0.0
- `test_partial_overlap` — Jaccard calculation verified
- `test_both_empty_tags` — Empty tags → 0.0
- `test_one_empty_tags` — One empty → 0.0
- `test_missing_tags_field` — Missing field handled gracefully

MMR rerank tests (9):
- `test_mmr_selects_diverse_categories` — 8 temples + 2 museums → picks museums for diversity
- `test_mmr_respects_lambda_zero` — Pure diversity mode
- `test_mmr_respects_lambda_one` — Pure relevance mode
- `test_empty_pois_returns_empty` — Empty input edge case
- `test_k_greater_than_pois_count` — k > n handled correctly
- `test_k_zero_returns_empty` — k=0 edge case
- `test_all_same_category` — All identical tags (similarity=1.0)
- `test_preserves_original_poi_dicts` — Returns references, not copies
- `test_default_parameters` — Defaults work correctly

**Full recommendation suite: 33/33 passed** (no regression in spatial_filter or scoring tests)

## Key Design Decisions

1. **Pure function** — No I/O, no side effects, deterministic
2. **Original dict preservation** — Uses list.pop() to move items, returns references
3. **Selection order** — Returned in MMR selection order (most relevant+diverse first)
4. **Defensive defaults** — Handles missing "score"/"tags" fields via `.get()`
