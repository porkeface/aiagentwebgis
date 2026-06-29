# Task 3.4: DBSCAN Clustering (Day Assignment)

**Files:**
- Create: `backend/recommendation/clustering.py`
- Test: `backend/tests/test_recommendation/test_clustering.py`

**Consumes:** POI list with lng/lat, number of days
**Produces:** list of day assignments: [{day: 1, pois: [...]}, ...]

**Steps:**

1. Implement cluster_pois_for_days(pois, n_days):
   - Extract (lat, lng) coordinates as numpy array
   - Try DBSCAN(eps=0.03, min_samples=2) -- ~3km in degrees
   - If DBSCAN produces wrong number of clusters, fallback to KMeans(n_clusters=n_days)
   - Sort clusters by centroid distance from city center
   - Map cluster index to day number

2. Write tests:
   - test_clustering_assigns_nearby_pois_same_day
   - test_clustering_splits_distant_pois
   - test_clustering_fallback_to_kmeans

3. Run tests, commit: `feat: DBSCAN clustering for day assignment with KMeans fallback`
