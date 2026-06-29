# Capability: Spatial Recommendation Engine

## Overview

5-step recommendation pipeline: spatial filtering → multi-factor scoring → MMR diversity reranking → spatial clustering for day assignment → TSP route optimization.

## Step 1: Spatial Filter

- **Input**: city name, optional bounding box
- **Process**: Query PostGIS with `ST_DWithin(location, center_point, radius)` or `ST_Within(location, city_boundary)`
- **Fallback**: If local data insufficient, supplement with Amap API
- **Output**: Candidate POI list (~50 POIs)

## Step 2: Multi-Factor Scoring

- **Scoring formula**: `score = w1*preference + w2*distance + w3*rating + w4*time + w5*popularity`
- **Weights**: Dynamically configured by Planner Agent based on user profile
- **Default weights**: preference=0.30, distance=0.20, rating=0.20, time=0.15, popularity=0.15
- **Each factor normalized to [0, 1]**:
  - `preference`: Jaccard similarity between POI tags and user preferences
  - `distance`: Inverse distance from city center / hotel (normalized)
  - `rating`: POI rating / 5.0
  - `time`: Binary (open now?) or seasonal suitability score
  - `popularity`: Normalized review count or visit frequency
- **Output**: Scored and sorted POI list (~20 POIs)

## Step 3: MMR Diversity Rerank

- **Algorithm**: Maximal Marginal Relevance
- **Formula**: `MMR(d) = argmax [λ * Relevance(d) - (1-λ) * max_sim(d, selected)]`
- **λ = 0.7**: Balance between relevance and diversity
- **Similarity**: Category overlap between POIs
- **Output**: Diverse selected POI list (~10-15 POIs)

## Step 4: Spatial Clustering (Day Assignment)

- **Algorithm**: DBSCAN on (latitude, longitude)
- **Parameters**: eps=3km, min_samples=2
- **Fallback**: If DBSCAN produces poor clusters (too few or too many), fall back to K-Means with k=days
- **Cluster-to-day mapping**: Sort clusters by centroid distance from hotel/city center, assign to Day 1, Day 2, etc.
- **Output**: `daily_pois: [{day: 1, pois: [...]}, {day: 2, pois: [...]}]`

## Step 5: TSP Route Optimization

- **Algorithm**: Nearest Neighbor heuristic → 2-opt improvement
- **Input**: Daily POI list per day
- **Distance matrix**: Computed via Amap walking/driving API (or Haversine for MVP)
- **Constraints**: Opening hours (time window), estimated stay duration
- **Output**: Optimized visiting order + polyline + per-segment distance/duration

## Acceptance Scenarios

1. City with 100 POIs → spatial filter reduces to ~50 → scoring selects top 20 → MMR picks 12 → clustering assigns 6 per day → TSP optimizes order
2. User with elderly companions → Agent sets distance weight=0.15, time weight=0.25 → flatter, more accessible POIs ranked higher
3. Two POIs same category "temple" within 500m → MMR ensures only one is selected unless user specifically wants temples
4. Day 1 cluster has POIs spanning 15km → DBSCAN eps=3km would split → correctly assigns to separate days or uses K-Means fallback
