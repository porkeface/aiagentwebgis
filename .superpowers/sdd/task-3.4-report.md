# Task 3.4 Report: DBSCAN Clustering (Day Assignment)

**Status:** DONE  
**Commit:** b8aaa86  
**Branch:** ai-travel-planner  
**Date:** 2026-06-29

## Summary

Implemented DBSCAN-based clustering algorithm to automatically assign POIs to different days of a trip based on geographic proximity. Falls back to KMeans when DBSCAN produces incorrect number of clusters.

## Implementation

### Files Created/Modified

1. **backend/recommendation/clustering.py** (new)
   - `cluster_pois_for_days(pois, n_days, center_lng, center_lat)` - main function
   - Uses DBSCAN(eps=0.03, min_samples=2) for ~3km clustering radius
   - Falls back to KMeans(n_clusters=n_days) when needed
   - Sorts clusters by distance from city center (closest = day 1)
   - Handles noise points and edge cases

2. **backend/tests/test_recommendation/test_clustering.py** (new)
   - 10 comprehensive tests covering:
     - Basic clustering (nearby POIs grouped together)
     - Distant POI separation
     - KMeans fallback
     - Center-based sorting
     - Immutability guarantees
   - All tests passing

3. **backend/recommendation/__init__.py** (modified)
   - Added `cluster_pois_for_days` to exports

### Algorithm Details

1. **DBSCAN Clustering**: 
   - eps=0.03 degrees ≈ 3km radius
   - min_samples=2 for core points
   - Automatically detects natural geographic clusters

2. **KMeans Fallback**:
   - Triggered when DBSCAN produces != n_days clusters
   - Ensures exactly n_days clusters are created

3. **Day Assignment**:
   - Calculates cluster centroids
   - Sorts by Euclidean distance from city center
   - Closest cluster = day 1, next = day 2, etc.
   - Uses POI centroid if no city center provided

4. **Noise Handling**:
   - DBSCAN noise points (label=-1) assigned to nearest cluster
   - Ensures all POIs are assigned to a day

### Test Results

```
======================== 10 passed, 1 warning in 3.47s ========================
```

All 43 recommendation engine tests passing (spatial_filter, scoring, mmr, clustering).

### Edge Cases Handled

- Empty POI list
- Single day (all POIs)
- Fewer POIs than days
- No city center provided (uses POI centroid)
- All POIs at same location (KMeans fallback)
- DBSCAN noise points
- Immutability: input POIs not mutated, returns copies

### Dependencies

- scikit-learn: 1.9.0 (already in requirements)
- numpy: 2.4.6 (already in requirements)

## Integration Points

- **Input**: POI list with `lat`, `lng` fields (from spatial_filter)
- **Output**: List of day assignments `[{day: 1, pois: [...]}, ...]`
- **Next**: Task 3.5 (TSP route optimization within each day)

## Notes

- Pure function, no I/O operations
- Uses Euclidean distance for sorting (not routing distance)
- KMeans convergence warning appears in test (expected with identical points)
- Follows project conventions: type hints, immutability, comprehensive error handling
