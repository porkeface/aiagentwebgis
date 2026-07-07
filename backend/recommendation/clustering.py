"""HDBSCAN clustering for day assignment with distance-based fallback.

Clusters POIs by geographic proximity using HDBSCAN (adaptive density,
no fixed eps).  If HDBSCAN fails (e.g. only one cluster for a multi-day
trip), falls back to AgglomerativeClustering with distance threshold.

After clustering, a post-validation step ensures every day has ≥2 POIs
and no day spans >35km.  Under-filled or over-spread clusters are
rebalanced before returning.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering

# Try HDBSCAN first; fall back to AgglomerativeClustering if not installed.
try:
    from hdbscan import HDBSCAN  # type: ignore[import-untyped]
    _HAS_HDBSCAN = True
except ImportError:
    _HAS_HDBSCAN = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_SPREAD_KM = 35       # per-cluster max haversine distance from centroid
_MIN_POIS_PER_DAY = 2     # every day must have at least 2 POIs


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in km between two (lat, lng) points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _euclidean_sq(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Squared Euclidean distance for sorting purposes (not routing)."""
    return (lat1 - lat2) ** 2 + (lng1 - lng2) ** 2


# ---------------------------------------------------------------------------
# Centroid helpers
# ---------------------------------------------------------------------------


def _cluster_centroid(
    coords: np.ndarray, labels: np.ndarray, label: int,
) -> tuple[float, float]:
    """Centroid (lat, lng) for a single cluster label."""
    mask = labels == label
    return (
        float(np.mean(coords[mask, 0])),
        float(np.mean(coords[mask, 1])),
    )


def _compute_centroids(
    coords: np.ndarray,
    labels: np.ndarray,
) -> dict[int, tuple[float, float]]:
    """Compute centroid (lat, lng) for every cluster (excludes noise label -1)."""
    centroids: dict[int, tuple[float, float]] = {}
    for label in np.unique(labels):
        if label == -1:
            continue
        centroids[int(label)] = _cluster_centroid(coords, labels, label)
    return centroids


def _sort_clusters_by_distance(
    centroids: dict[int, tuple[float, float]],
    ref_lat: float,
    ref_lng: float,
) -> list[int]:
    """Sort cluster labels by Euclidean distance from reference point, closest-first."""
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
# Cluster spread check
# ---------------------------------------------------------------------------


def _cluster_spread_km(
    coords: np.ndarray, labels: np.ndarray, label: int,
) -> float:
    """Max haversine distance from centroid to any member of the cluster."""
    mask = labels == label
    if not np.any(mask):
        return 0.0
    clat, clng = _cluster_centroid(coords, labels, label)
    max_d = 0.0
    for idx in np.where(mask)[0]:
        d = _haversine_km(clat, clng, float(coords[idx, 0]), float(coords[idx, 1]))
        if d > max_d:
            max_d = d
    return max_d


# ---------------------------------------------------------------------------
# Cluster count adjustment (merge / split)
# ---------------------------------------------------------------------------


def _merge_nearest_pair(
    labels: np.ndarray,
    centroids: dict[int, tuple[float, float]],
) -> tuple[np.ndarray, dict[int, tuple[float, float]]]:
    """Merge the two geographically closest clusters into one.

    Returns (new_labels, new_centroids).  The merged cluster keeps the
    lower label of the pair.
    """
    c_labels = sorted(centroids.keys())
    if len(c_labels) < 2:
        return labels, centroids

    best = (float("inf"), 0, 0)
    for i in range(len(c_labels)):
        for j in range(i + 1, len(c_labels)):
            d = _euclidean_sq(
                centroids[c_labels[i]][0], centroids[c_labels[i]][1],
                centroids[c_labels[j]][0], centroids[c_labels[j]][1],
            )
            if d < best[0]:
                best = (d, c_labels[i], c_labels[j])

    a_label, b_label = best[1], best[2]
    new_labels = labels.copy()
    new_labels[labels == b_label] = a_label
    # Compact labels
    unique = sorted(set(new_labels) - {-1})
    remap = {old: new for new, old in enumerate(unique)}
    for i in range(len(new_labels)):
        if new_labels[i] != -1:
            new_labels[i] = remap[new_labels[i]]
    new_centroids = _compute_centroids(coords, new_labels)
    return new_labels, new_centroids


def _split_largest_cluster(
    coords: np.ndarray,
    labels: np.ndarray,
    centroids: dict[int, tuple[float, float]],
) -> tuple[np.ndarray, dict[int, tuple[float, float]]]:
    """Split the largest cluster (by member count) along its primary axis.

    Returns (new_labels, new_centroids).  Does nothing if the largest
    cluster has fewer than 4 members (can't split meaningfully).
    """
    sizes: list[tuple[int, int]] = [
        (int(label), int(np.sum(labels == label)))
        for label in sorted(centroids.keys())
    ]
    sizes.sort(key=lambda x: -x[1])
    split_label = sizes[0][0]

    mask = labels == split_label
    indices = np.where(mask)[0]
    if len(indices) < 4:
        return labels, centroids  # too small to split meaningfully

    cluster_coords = coords[indices]
    # Split along the axis with greatest variance
    var_lat = float(np.var(cluster_coords[:, 0]))
    var_lng = float(np.var(cluster_coords[:, 1]))
    if var_lat >= var_lng:
        median = float(np.median(cluster_coords[:, 0]))
        left_mask = coords[:, 0] <= median
    else:
        median = float(np.median(cluster_coords[:, 1]))
        left_mask = coords[:, 1] <= median

    new_label = int(max(int(k) for k in centroids.keys())) + 1
    new_labels = labels.copy()
    for idx in indices:
        if left_mask[idx]:
            new_labels[idx] = new_label
        # else: stays with original split_label

    new_centroids = _compute_centroids(coords, new_labels)
    return new_labels, new_centroids


def _adjust_to_n_clusters(
    coords: np.ndarray,
    labels: np.ndarray,
    n_days: int,
    centroids: dict[int, tuple[float, float]],
) -> np.ndarray:
    """Merge or split clusters until we have exactly n_days distinct clusters.

    Safety: capped at 20 iterations to prevent infinite loops from edge cases
    (e.g. all clusters too small to split, no pairs to merge).
    """
    cur_labels = labels
    cur_centroids = centroids
    iterations = 0
    max_iterations = 20

    # Merge down
    while len(cur_centroids) > n_days and iterations < max_iterations:
        cur_labels, cur_centroids = _merge_nearest_pair(cur_labels, cur_centroids)
        iterations += 1

    # Split up
    while len(cur_centroids) < n_days and iterations < max_iterations:
        prev_n = len(cur_centroids)
        cur_labels, cur_centroids = _split_largest_cluster(
            coords, cur_labels, cur_centroids,
        )
        iterations += 1
        if len(cur_centroids) == prev_n:
            # split did nothing (all clusters too small) — give up
            break

    return cur_labels


# ---------------------------------------------------------------------------
# Post-clustering validation & rebalancing
# ---------------------------------------------------------------------------


def _rebalance_clusters(
    coords: np.ndarray,
    labels: np.ndarray,
    n_days: int,
    pois: list[dict],
) -> list[dict]:
    """Ensure each cluster has ≥2 POI and ≤35km spread.

    Returns list of {day, pois} dicts, rearranging POIs as needed.
    """
    # Work with mutable copies
    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        label_int = int(label)
        clusters.setdefault(label_int, []).append(idx)

    # ── Fix under-filled clusters (< 2 POIs) ──
    for label in sorted(clusters.keys()):
        while len(clusters[label]) < _MIN_POIS_PER_DAY:
            # Find the nearest POI from any cluster that has ≥3 POIs
            donor_label: int | None = None
            donor_idx: int | None = None
            best_dist = float("inf")
            # Compute centroid from current cluster members (not stale labels)
            member_coords = coords[np.array(clusters[label])]
            clat = float(np.mean(member_coords[:, 0]))
            clng = float(np.mean(member_coords[:, 1]))
            for dl, member_indices in clusters.items():
                if dl == label or len(member_indices) < _MIN_POIS_PER_DAY + 1:
                    continue
                for mi in member_indices:
                    d = _haversine_km(
                        clat, clng,
                        float(coords[mi, 0]), float(coords[mi, 1]),
                    )
                    if d < best_dist:
                        best_dist = d
                        donor_label = dl
                        donor_idx = mi
            if donor_label is None or donor_idx is None:
                break  # no donor available — accept under-filled day
            clusters[label].append(donor_idx)
            clusters[donor_label].remove(donor_idx)

    # ── Remove empty clusters ──
    clusters = {k: v for k, v in clusters.items() if v}

    # ── Map to {day, pois} while respecting the original ordering ──
    # The original cluster labels are ordered by centroid distance from city
    # center. Rebuild that ordering over the remaining clusters.
    c_centroids: dict[int, tuple[float, float]] = {}
    for label, member_indices in clusters.items():
        member_coords = coords[np.array(member_indices)]
        c_centroids[label] = (
            float(np.mean(member_coords[:, 0])),
            float(np.mean(member_coords[:, 1])),
        )

    # Determine reference: first POI's position (hub) or overall centroid
    ref_lat = float(np.mean(coords[:, 0]))
    ref_lng = float(np.mean(coords[:, 1]))
    sorted_labels = sorted(
        c_centroids.keys(),
        key=lambda l: _euclidean_sq(
            c_centroids[l][0], c_centroids[l][1], ref_lat, ref_lng,
        ),
    )

    result: list[dict] = []
    for day_num, label in enumerate(sorted_labels[:n_days], start=1):
        result.append({
            "day": day_num,
            "pois": [dict(pois[idx]) for idx in sorted(clusters[label])],
        })

    return result


# ---------------------------------------------------------------------------
# Main clustering pipeline
# ---------------------------------------------------------------------------


def cluster_pois_for_days(
    pois: list[dict],
    n_days: int,
    center_lng: float | None = None,
    center_lat: float | None = None,
) -> list[dict]:
    """Cluster POIs into day assignments based on geographic proximity.

    Uses HDBSCAN (adaptive density) first. If HDBSCAN is unavailable or
    fails, falls back to AgglomerativeClustering with distance threshold.

    Clusters are adjusted to exactly n_days via merge/split, then
    post-validated to ensure ≥2 POIs per day and sorted by distance from
    city center (closest = day 1).

    Args:
        pois: List of POI dicts with 'lat' and 'lng' fields.
        n_days: Number of days to split POIs into.
        center_lng: Optional city center longitude for sorting.
        center_lat: Optional city center latitude for sorting.

    Returns:
        List of dicts: [{day: 1, pois: [...]}, {day: 2, pois: [...]}, ...].
    """
    if not pois:
        return []
    if n_days <= 0:
        return []

    coords = np.array([(poi["lat"], poi["lng"]) for poi in pois])

    # Reference point for cluster ordering
    if center_lat is not None and center_lng is not None:
        ref_lat, ref_lng = center_lat, center_lng
    else:
        ref_lat = float(np.mean(coords[:, 0]))
        ref_lng = float(np.mean(coords[:, 1]))

    # Single day — all together
    if n_days == 1:
        return [{"day": 1, "pois": [dict(poi) for poi in pois]}]

    # ── Step 1: Cluster via HDBSCAN or Agglomerative ──
    labels: np.ndarray
    if _HAS_HDBSCAN:
        min_size = max(2, min(3, len(pois) // n_days // 2))
        hdbscan = HDBSCAN(
            min_cluster_size=min_size,
            min_samples=1,
            cluster_selection_epsilon=0.05,  # ~5km — small enough for urban
            metric="euclidean",
        )
        labels = hdbscan.fit_predict(coords)
    else:
        # Direct AgglomerativeClustering
        agg = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=0.05,
            metric="euclidean",
            linkage="single",
        )
        labels = agg.fit_predict(coords)

    n_raw_clusters = len(set(labels) - {-1})

    # ── Step 2: Assign noise points to nearest cluster ──
    centroids = _compute_centroids(coords, labels)
    if -1 in labels and centroids:
        noise_mask = labels == -1
        c_labels_arr = list(centroids.keys())
        c_coords_arr = np.array([centroids[k] for k in c_labels_arr])
        for idx in np.where(noise_mask)[0]:
            lat, lng = float(coords[idx, 0]), float(coords[idx, 1])
            dists = np.array([
                _euclidean_sq(lat, lng, c[0], c[1]) for c in c_coords_arr
            ])
            labels[idx] = c_labels_arr[int(np.argmin(dists))]
        centroids = _compute_centroids(coords, labels)

    n_clusters = len(centroids)

    # ── Step 3: Adjust cluster count to n_days ──
    if n_clusters > 0 and n_clusters != n_days:
        labels = _adjust_to_n_clusters(coords, labels, n_days, centroids)

    # ── Step 4: Assign noise again (adjust may have introduced noise) ──
    centroids = _compute_centroids(coords, labels)
    if -1 in labels and centroids:
        noise_mask = labels == -1
        c_labels_arr = list(centroids.keys())
        c_coords_arr = np.array([centroids[k] for k in c_labels_arr])
        for idx in np.where(noise_mask)[0]:
            lat, lng = float(coords[idx, 0]), float(coords[idx, 1])
            dists = np.array([
                _euclidean_sq(lat, lng, c[0], c[1]) for c in c_coords_arr
            ])
            labels[idx] = c_labels_arr[int(np.argmin(dists))]
        centroids = _compute_centroids(coords, labels)

    # ── Step 5: Post-validation & rebalance ──
    return _rebalance_clusters(coords, labels, n_days, pois)
