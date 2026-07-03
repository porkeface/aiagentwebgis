"""Recommendation engine package.

Only the actively-used `cluster_pois_for_days` helper lives here — it is
imported by `agent/tools/geo_partition.py`. The pipeline / scoring / mmr /
spatial_filter / tsp modules were removed during the B-23 cleanup as dead
code superseded by `agent/tools/spatial_analysis.py` and the deterministic
planning pipeline in `agent/graph_v2.py`.
"""

from recommendation.clustering import cluster_pois_for_days

__all__ = ["cluster_pois_for_days"]
