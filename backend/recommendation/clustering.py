"""DBSCAN clustering for day assignment with KMeans fallback — pure function, no I/O.

Clusters POIs by geographic proximity using DBSCAN (eps=0.03 degrees ≈ 3km).
If DBSCAN does not produce the desired number of clusters, falls back to KMeans.
Clusters are sorted by centroid distance from city center (or POI centroid if
no center is given), then mapped to day numbers (closest = day 1).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import DBSCAN, KMeans


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _euclidean_sq(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Squared Euclidean distance for sorting purposes (not routing)."""
    return (lat1 - lat2) ** 2 + (lng1 - lng2) ** 2


def _compute_centroids(
    coords: np.ndarray,
    labels: np.ndarray,
) -> dict[int, tuple[float, float]]:
    """Compute centroid (lat, lng) for each cluster label.

    Returns dict mapping label -> (mean_lat, mean_lng).
    """
    centroids: dict[int, tuple[float, float]] = {}
    unique_labels = np.unique(labels)
    for label in unique_labels:
        if label == -1:
            continue
        mask = labels == label
        cluster_coords = coords[mask]
        centroids[int(label)] = (
            float(np.mean(cluster_coords[:, 0])),
            float(np.mean(cluster_coords[:, 1])),
        )
    return centroids


def _assign_noise_to_nearest(
    coords: np.ndarray,
    labels: np.ndarray,
    centroids: dict[int, tuple[float, float]],
) -> np.ndarray:
    """Assign noise points (label == -1) to the nearest non-noise cluster."""
    if not centroids:
        # All noise — nothing to assign to
        return labels

    result = labels.copy()
    noise_mask = labels == -1

    if not np.any(noise_mask):
        return result

    centroid_labels = list(centroids.keys())
    centroid_arr = np.array([centroids[k] for k in centroid_labels])

    noise_indices = np.where(noise_mask)[0]
    for idx in noise_indices:
        lat, lng = float(coords[idx, 0]), float(coords[idx, 1])
        dists = np.array([
            _euclidean_sq(lat, lng, c[0], c[1]) for c in centroid_arr
        ])
        nearest_idx = int(np.argmin(dists))
        result[idx] = centroid_labels[nearest_idx]

    return result


def _sort_clusters_by_distance(
    centroids: dict[int, tuple[float, float]],
    ref_lat: float,
    ref_lng: float,
) -> list[int]:
    """Sort cluster labels by Euclidean distance from reference point.

    Returns list of cluster labels ordered closest-first.
    """
    return sorted(
        centroids.keys(),
        key=lambda label: _euclidean_sq(
            centroids[label][0],
            centroids[label][1],
            ref_lat,
            ref_lng,
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cluster_pois_for_days(
    pois: list[dict],
    n_days: int,
    center_lng: float | None = None,
    center_lat: float | None = None,
) -> list[dict]:
    """Cluster POIs into day assignments based on geographic proximity.

    Uses DBSCAN (eps=0.03° ≈ 3km, min_samples=2) first. If DBSCAN does not
    produce exactly n_days clusters, falls back to KMeans(n_clusters=n_days).
    Clusters are sorted by centroid distance from city center (closest = day 1).

    Args:
        pois: List of POI dicts with 'lat' and 'lng' fields.
        n_days: Number of days to split POIs into.
        center_lng: Optional city center longitude for sorting.
        center_lat: Optional city center latitude for sorting.

    Returns:
        List of dicts: [{day: 1, pois: [...]}, {day: 2, pois: [...]}, ...].
        Each POI in 'pois' is a copy (input dicts are not mutated).
    """
    if not pois:
        return []

    if n_days <= 0:
        return []

    # Extract coordinates: (lat, lng)
    coords = np.array([(poi["lat"], poi["lng"]) for poi in pois])

    # Determine reference point for sorting
    if center_lat is not None and center_lng is not None:
        ref_lat, ref_lng = center_lat, center_lng
    else:
        # Use centroid of all POIs as reference
        ref_lat = float(np.mean(coords[:, 0]))
        ref_lng = float(np.mean(coords[:, 1]))

    # Edge case: single day — all POIs together
    if n_days == 1:
        return [{"day": 1, "pois": [dict(poi) for poi in pois]}]

    # Try DBSCAN
    dbscan = DBSCAN(eps=0.03, min_samples=2)
    labels = dbscan.fit_predict(coords)
    n_dbscan_clusters = len(set(labels) - {-1})

    # Check if DBSCAN produced exactly n_days clusters
    if n_dbscan_clusters == n_days:
        centroids = _compute_centroids(coords, labels)
        # Handle noise points
        if -1 in labels:
            labels = _assign_noise_to_nearest(coords, labels, centroids)
            centroids = _compute_centroids(coords, labels)
        sorted_labels = _sort_clusters_by_distance(centroids, ref_lat, ref_lng)
        label_to_day = {label: day + 1 for day, label in enumerate(sorted_labels)}
    else:
        # Fallback to KMeans
        effective_clusters = min(n_days, len(pois))
        kmeans = KMeans(n_clusters=effective_clusters, n_init=10, random_state=42)
        labels = kmeans.fit_predict(coords)
        centroids = _compute_centroids(coords, labels)
        sorted_labels = _sort_clusters_by_distance(centroids, ref_lat, ref_lng)
        label_to_day = {label: day + 1 for day, label in enumerate(sorted_labels)}

    # Group POIs by day
    days_map: dict[int, list[dict]] = {}
    for day_num in range(1, n_days + 1):
        days_map[day_num] = []

    for idx, poi in enumerate(pois):
        day_num = label_to_day.get(int(labels[idx]), 1)
        if day_num > n_days:
            # If KMeans gave more clusters than n_days, merge extras into last day
            day_num = n_days
        days_map[day_num].append(dict(poi))

    return [{"day": day, "pois": days_map[day]} for day in range(1, n_days + 1)]
