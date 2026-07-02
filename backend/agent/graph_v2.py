"""Graph v2 — intent router + LLM-driven planning pipeline.

Adds a ``classify_intent`` node before the ReAct loop.  For trip planning
requests the graph takes an LLM-enhanced pipeline with dynamic search
strategy, POI alignment, Critic validation, and duration-based capacity.

Graph topology::

    START
      │
      ▼
  classify_intent ──(chat/poi/route)──► agent_node ⇄ tools_node
      │                                      │
      │(trip_planning)                       └──► END
      ▼
  planning_pipeline ──────────────────────► agent_node (summary) ──► END

Pipeline steps:
0. Xiaohongshu guide search → LLM extract route info
1. LLM dynamic search strategy (city-specific categories)
2. Parallel POI search + guide-spot alignment
3. Score POIs by preference/distance/rating/popularity
4. Estimate visit durations for dynamic daily capacity
5. Geo-partition into daily clusters
6. Route each day via Amap waypoint API
7. Multi-round Critic LLM validation
8. Validate and submit plan

The existing ReAct agent_node + tools_node loop is preserved for POI queries,
route queries, and chitchat — those are naturally short (1-2 tool calls).
"""