"""Recommendation pipeline orchestration - 5-step workflow.

Pipeline steps:
1. Spatial filter - get candidate POIs near city center
2. Score - multi-factor scoring with user preferences
3. MMR rerank - diversity-aware selection
4. Cluster - assign POIs to days based on geography
5. Route optimization - TSP for each day

Entry point: run_recommendation_pipeline()
"""

from __future__ import annotations

from typing import Any

from recommendation.clustering import cluster_pois_for_days
from recommendation.mmr import mmr_rerank
from recommendation.scoring import score_pois
from recommendation.spatial_filter import spatial_filter_pois
from recommendation.tsp import optimize_daily_route


async def run_recommendation_pipeline(
    city: str,
    preferences: list[str],
    days: int,
    weights: dict[str, float],
    center_lng: float,
    center_lat: float,
    lambda_mmr: float = 0.7,
    mmr_k: int = 12,
) -> dict[str, Any]:
    """Execute full recommendation pipeline.

    Args:
        city: City name for POI search.
        preferences: User preference tags (e.g. ['culture', 'history']).
        days: Number of trip days.
        weights: Scoring weights for each factor.
        center_lng: City center longitude (EPSG:4326).
        center_lat: City center latitude (EPSG:4326).
        lambda_mmr: MMR diversity trade-off (0.0=diversity, 1.0=relevance).
        mmr_k: Number of diverse POIs to select.

    Returns:
        {
            "candidate_count": int,
            "scored_count": int,
            "diverse_count": int,
            "daily_plans": [
                {
                    "day": int,
                    "pois": [ordered POIs with scores],
                    "total_distance_km": float,
                    "segments": [...]
                },
                ...
            ]
        }
    """
    # Step 1: Spatial filter - get candidates
    candidates, _needs_api = await spatial_filter_pois(
        city=city,
        center_lng=center_lng,
        center_lat=center_lat,
    )
    candidate_count = len(candidates)

    # Step 2: Score POIs with user preferences
    scored = score_pois(
        pois=candidates,
        preferences=preferences,
        weights=weights,
        center_lng=center_lng,
        center_lat=center_lat,
    )
    scored_count = len(scored)

    # Step 3: MMR rerank for diversity
    diverse = mmr_rerank(
        pois=scored,
        lambda_=lambda_mmr,
        k=mmr_k,
    )
    diverse_count = len(diverse)

    # Step 4: Cluster POIs into daily assignments
    daily_clusters = cluster_pois_for_days(
        pois=diverse,
        n_days=days,
        center_lng=center_lng,
        center_lat=center_lat,
    )

    # Step 5: Optimize route for each day
    daily_plans: list[dict[str, Any]] = []
    for cluster in daily_clusters:
        day_num = cluster["day"]
        day_pois = cluster["pois"]

        # Optimize route for this day
        route_result = optimize_daily_route(
            pois=day_pois,
            center_lng=center_lng,
            center_lat=center_lat,
        )

        daily_plans.append(
            {
                "day": day_num,
                "pois": route_result["ordered_pois"],
                "total_distance_km": route_result["total_distance_km"],
                "segments": route_result["segments"],
            }
        )

    # Assemble result
    return {
        "candidate_count": candidate_count,
        "scored_count": scored_count,
        "diverse_count": diverse_count,
        "daily_plans": daily_plans,
    }
