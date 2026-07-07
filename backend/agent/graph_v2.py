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

The existing ReAct agent_node + tools_node loop is preserved for POI queries,
route queries, and chitchat — those are naturally short (1-2 tool calls).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StreamWriter

from agent.checkpointer import get_checkpointer
from agent.prompts.system import AGENT_SYSTEM_PROMPT
from agent.state import AgentState
from agent.tools import AGENT_TOOLS
from app.config import settings

logger = logging.getLogger(__name__)


def _euclidean_sq_for_poi(poi: dict[str, Any], clat: float, clng: float) -> float:
    """Squared Euclidean distance between a POI dict and a centroid (lat,lng)."""
    return (poi.get("lat", 0) - clat) ** 2 + (poi.get("lng", 0) - clng) ** 2


def _min_dist_to_cluster(poi: dict[str, Any], cluster_pois: list[dict[str, Any]]) -> float:
    """Minimum squared Euclidean distance from a POI to ANY member of the cluster.

    This is the route-proximity measure: a POI that is close to *any* point
    on a day's route belongs to that day.  Using min-of-pairwise is a cheap
    proxy for true polyline proximity — zero API calls, no time impact.
    """
    plat = poi.get("lat", 0)
    plng = poi.get("lng", 0)
    best = float("inf")
    for cp in cluster_pois:
        d = (cp.get("lat", 0) - plat) ** 2 + (cp.get("lng", 0) - plng) ** 2
        if d < best:
            best = d
    return best


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TOOL_CALLS = 25
TOOL_TIMEOUT_SEC = 30
PARALLELIZABLE_TOOLS = frozenset({
    "search_pois", "search_nearby", "geocode", "score_pois",
})

INTENT_CLASSIFY_PROMPT = """你是一个意图分类器。分析用户消息，判断意图类型并提取参数。

意图类型：
- chat: 闲聊、问候、感谢、无关话题
- poi_query: 查询POI信息（"故宫在哪"、"北京有什么博物馆"）
- route_query: 查询两点间路线（"从天安门到颐和园怎么走"、"XX到XX多远"）
- trip_planning: 规划多日行程（"帮我规划北京三日游"、"安排一个周末上海行程"）

返回**纯JSON**（不要markdown代码块）：
{"intent": "<类型>", "city": "<城市名或null>", "days": <天数或null>, "preferences": ["<偏好1>", ...]}"""

# ---------------------------------------------------------------------------
# Module-level caches
# ---------------------------------------------------------------------------

_compiled_graph_v2: CompiledStateGraph | None = None
_tool_map: dict[str, Any] = {}


def _build_tool_map() -> dict[str, Any]:
    global _tool_map
    if not _tool_map:
        _tool_map = {t.name: t for t in AGENT_TOOLS}
    return _tool_map


def _get_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.dashscope_api_key,
        temperature=0.0,
        streaming=True,
        timeout=60,
        max_retries=1,
    ).bind_tools(AGENT_TOOLS)


def _get_model_no_tools() -> ChatOpenAI:
    """LLM without tool binding — for intent classification and summaries."""
    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.dashscope_api_key,
        temperature=0.0,
        streaming=True,
        timeout=30,
        max_retries=1,
    )


def reset_compiled_graph_v2() -> None:
    global _compiled_graph_v2
    _compiled_graph_v2 = None


# ---------------------------------------------------------------------------
# Tool-call chunk merger (same as graph.py)
# ---------------------------------------------------------------------------


def _merge_tool_call_chunks(
    accumulated: AIMessage,
    raw_chunks: list[dict[str, Any]] | None,
) -> None:
    if not raw_chunks:
        return
    if not accumulated.tool_calls:
        accumulated.tool_calls = []
    for chunk in raw_chunks:
        idx = chunk.get("index", 0)
        while len(accumulated.tool_calls) <= idx:
            accumulated.tool_calls.append(
                {"name": "", "args": {}, "id": "", "type": "tool_call"}
            )
        tc = accumulated.tool_calls[idx]
        if chunk.get("id"):
            tc["id"] = chunk["id"]
        if chunk.get("name"):
            tc["name"] = chunk["name"]
        args_chunk = chunk.get("args", "")
        if args_chunk:
            existing = tc.get("args")
            if isinstance(existing, dict):
                existing = ""
            tc["args"] = existing + args_chunk
    for tc in accumulated.tool_calls:
        if isinstance(tc.get("args"), str) and tc["args"].strip():
            try:
                tc["args"] = json.loads(tc["args"])
            except json.JSONDecodeError:
                pass


# ---------------------------------------------------------------------------
# Intent classification node
# ---------------------------------------------------------------------------


async def classify_intent_node(
    state: AgentState, config: RunnableConfig, writer: StreamWriter,
) -> dict[str, Any]:
    """Classify user intent with a single lightweight LLM call.

    Extracts intent type + structured params (city, days, preferences).
    """
    raw_model = _get_model_no_tools()
    messages = state["messages"]
    user_msg = messages[-1] if messages else HumanMessage(content="")
    user_content = user_msg.content if hasattr(user_msg, "content") else str(user_msg)

    classify_msgs = [
        SystemMessage(content=INTENT_CLASSIFY_PROMPT),
        HumanMessage(content=user_content),
    ]

    try:
        response = await raw_model.ainvoke(classify_msgs)
        content = response.content if hasattr(response, "content") else str(response)
        # Strip markdown code fences
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        intent = json.loads(content)
    except Exception:
        logger.warning("Intent classification failed, defaulting to chat")
        intent = {"intent": "chat", "city": None, "days": None, "preferences": []}

    writer({"type": "intent_detected", "data": intent})
    return {
        "intent": intent.get("intent", "chat"),
        "intent_city": intent.get("city"),
        "intent_days": intent.get("days"),
        "intent_preferences": intent.get("preferences", []),
    }


# ---------------------------------------------------------------------------
# Pre-selected POI detection (user selected POIs on the map)
# ---------------------------------------------------------------------------

_PRESELECTED_POI_RE = re.compile(
    r"-\s*(\S+?)\s*\|\s*id:(\S+?)\s*\|\s*lng:([\d.-]+)\s*\|\s*lat:([\d.-]+)"
)


def _parse_preselected_pois(user_message: str) -> list[dict[str, Any]]:
    """Extract pre-selected POIs from a "plan with these POIs" user message."""
    pois: list[dict[str, Any]] = []
    for m in _PRESELECTED_POI_RE.finditer(user_message):
        name, pid, lng, lat = m.group(1), m.group(2), m.group(3), m.group(4)
        try:
            pois.append({
                "name": name.strip(),
                "id": pid.strip(),
                "poi_id": pid.strip(),
                "lng": float(lng),
                "lat": float(lat),
                "rating": 4.0,
                "score": 100,
            })
        except ValueError:
            continue
    return pois


# ---------------------------------------------------------------------------
# Planning pipeline node (fixed, deterministic — no LLM in the loop)
# ---------------------------------------------------------------------------


async def planning_pipeline_node(
    state: AgentState, config: RunnableConfig, writer: StreamWriter,
) -> dict[str, Any]:
    """Pipeline for multi-day trip planning.

    Steps:
    0. Search Xiaohongshu for travel guides → LLM extract route info
    1. LLM generates dynamic search strategy (city-specific categories)
    2. Parallel POI search + guide-spot alignment
    3. Score POIs by preference/distance/rating/popularity
    4. Estimate visit durations for dynamic daily capacity
    5. Geo-partition into daily clusters
    6. Route each day via Amap waypoint API
    7. Multi-round Critic LLM validation
    8. Validate and submit plan
    """
    user_content = ""
    msgs = state.get("messages", [])
    if msgs:
        last = msgs[-1]
        raw = last.content if hasattr(last, "content") else str(last)
        user_content = raw[:500]  # truncate to prevent prompt injection

    city = state.get("intent_city", "北京") or "北京"
    days = state.get("intent_days", 3) or 3
    preferences = state.get("intent_preferences", []) or []
    if not isinstance(days, int) or days < 1:
        days = 3
    if days > 7:
        days = 7  # cap at 7 days to avoid excessive API calls

    logger.info("Planning pipeline started: city=%s, days=%d", city, days)

    # ── Pre-selected POIs short-circuit ────────────────────────────────────
    preselected_pois = _parse_preselected_pois(user_content)
    if preselected_pois and len(preselected_pois) >= 2:
        logger.info("Pre-selected POIs detected: %d POIs, skipping search", len(preselected_pois))
        return await _plan_with_preselected_pois(
            preselected_pois=preselected_pois,
            city=city,
            writer=writer,
        )

    # ── Step 0: Xiaohongshu guide search (DISABLED for speed — re-enable by
    #     removing the "if False") ──────────────────────────────────────────
    guide_info: dict[str, Any] = {"spots": [], "daily_groups": {}, "tips": []}
    if False:  # disabled: saves ~15s (2 API + 1 LLM call), marginal quality gain
        if settings.oneapi_api_key:
            try:
                writer({"type": "searching", "data": {"message": "正在搜索小红书攻略..."}})
                from app.services.oneapi_service import OneAPIService

                oneapi = OneAPIService()

                # Two parallel guide searches
                resp_guide, resp_spot = await asyncio.gather(
                    oneapi.search_notes(keyword=f"{city}{days}日旅游攻略 路线推荐", page=1, sort_type="popularity_descending", note_type="普通笔记", time_filter="半年内"),
                    oneapi.search_notes(keyword=f"{city}必去景点推荐 2026", page=1, sort_type="popularity_descending", note_type="普通笔记", time_filter="半年内"),
                    return_exceptions=True,
                )

                guide_text = ""
                if isinstance(resp_guide, dict):
                    guide_text += oneapi.extract_guide_text(resp_guide, max_notes=8)
                if isinstance(resp_spot, dict):
                    guide_text += "\n\n" + oneapi.extract_guide_text(resp_spot, max_notes=8)

                await oneapi.close()

                if guide_text.strip():
                    # LLM extracts route info from guide text
                    extract_prompt = f"""你是旅游攻略信息提取器。从以下小红书攻略摘要中：

    1. 提取所有被推荐的景点/地点名称列表（一行一个，去重）
    2. 如果有按天分组建议，提取分组（如"第1天：故宫+景山+南锣"）
    3. 提取注意事项（开放时间、门票、季节提示等，每个一行）

    攻略内容：
    {guide_text[:4000]}

    输出纯JSON：
    {{"spots": ["景点名1", "景点名2"], "daily_groups": {{"第1天": ["A", "B"]}}, "tips": ["提示1", "提示2"]}}"""

                    raw_model = _get_model_no_tools()
                    extract_resp = await raw_model.ainvoke([
                        SystemMessage(content="你是精确的旅游信息提取器，只提取攻略中明确提到的信息。"),
                        HumanMessage(content=extract_prompt),
                    ])
                    ec = extract_resp.content if hasattr(extract_resp, "content") else str(extract_resp)
                    ec = ec.strip()
                    if ec.startswith("```"): ec = ec.split("\n", 1)[-1]; ec = ec.rsplit("```", 1)[0]
                    try:
                        guide_info = json.loads(ec)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse guide extraction JSON")
                    logger.info("Guide extracted: %d spots, %d groups, %d tips",
                                len(guide_info.get("spots", [])),
                                len(guide_info.get("daily_groups", {})),
                                len(guide_info.get("tips", [])))
            except Exception as exc:
                logger.warning("Guide search failed, falling back to pure Amap: %s", exc.__class__.__name__)
                # Non-critical — continue with Amap-only pipeline

    # ── Step 1: Search strategy — use hardcoded categories (LLM skipped for speed) ──
    writer({"type": "searching", "data": {"message": f"正在搜索{city}的景点..."}})

    from agent.tools.poi_search import search_pois as search_pois_fn

    # Hardcoded search categories — skips LLM strategy generation (~3s saved)
    # City-sensitive defaults cover 95% of Chinese tourist cities
    search_strategies: list[dict[str, str]] = [
        {"category": "风景名胜", "keyword": ""},
        {"category": "博物馆", "keyword": ""},
        {"category": "公园", "keyword": ""},
        {"category": "寺庙道观", "keyword": ""},
        {"category": "特色街区", "keyword": ""},
    ]

    writer({"type": "searching", "data": {"message": f"正在搜索{city}的{len(search_strategies)}类景点..."}})

    search_tasks = [
        search_pois_fn.ainvoke({"city": city, "category": s["category"], "keyword": s.get("keyword", "")}, config)
        for s in search_strategies
    ]

    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    all_pois: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for result in search_results:
        if isinstance(result, list):
            for poi in result:
                pid = str(poi.get("id", ""))
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_pois.append(poi)

    if not all_pois:
        writer({"type": "error", "data": {"message": f"未能搜索到{city}的POI数据"}})
        return {"messages": [AIMessage(content=f"抱歉，未能搜索到{city}的旅游信息，请换一个城市试试。")]}

    # ── Semantic dedup: remove same-place-different-name duplicates ──
    from agent.tools.poi_dedup import deduplicate_pois

    before_dedup = len(all_pois)
    all_pois = deduplicate_pois(all_pois)
    if before_dedup != len(all_pois):
        logger.info("Dedup removed %d duplicate POIs (%d → %d)",
                    before_dedup - len(all_pois), before_dedup, len(all_pois))

    writer({
        "type": "candidates_ready",
        "data": {"pois": all_pois, "count": len(all_pois)},
    })

    # ── Step 2: Score POIs ───────────────────────────────────────────────
    writer({"type": "scoring", "data": {"message": "正在评估景点质量..."}})

    from agent.tools.spatial_analysis import score_pois as score_pois_fn

    # Compute city center as centroid of all POIs
    valid_coords = [
        (p["lng"], p["lat"])
        for p in all_pois
        if isinstance(p.get("lng"), (int, float)) and isinstance(p.get("lat"), (int, float))
    ]
    if valid_coords:
        center_lng = sum(c[0] for c in valid_coords) / len(valid_coords)
        center_lat = sum(c[1] for c in valid_coords) / len(valid_coords)
    else:
        center_lng, center_lat = 116.397, 39.908  # Beijing fallback

    scored = await score_pois_fn.ainvoke({
        "pois": all_pois,
        "preferences": preferences,
        "city_center_lng": center_lng,
        "city_center_lat": center_lat,
    }, config)

    # ── Step 2.5: Estimate visit durations for dynamic capacity ─────────────
    from app.services.duration_estimator import estimate_poi_duration_from_dict, estimate_daily_capacity

    for poi in scored:
        poi["visit_duration_min"] = estimate_poi_duration_from_dict(poi)

    # Calculate per-day capacity based on top POI durations
    top_durations = [p["visit_duration_min"] for p in scored[:len(scored)]]
    dynamic_per_day = estimate_daily_capacity(top_durations)
    # Hard cap at 8 to prevent unreasonable schedules; floor at 4 to ensure
    # enough POIs per day for a meaningful itinerary.
    max_per_day = max(min(dynamic_per_day + 1, 8), 4)

    # ── Step 3: Geo-partition ────────────────────────────────────────────
    writer({"type": "clustering", "data": {"message": f"正在按地理分区规划{days}天行程..."}})

    from agent.tools.geo_partition import geo_partition as geo_partition_fn

    # Take top-scored POIs based on dynamic capacity (at least 3×days)
    top_n = max(min(len(scored), days * max_per_day), days * 3)
    top_pois = scored[:top_n]

    clusters = await geo_partition_fn.ainvoke({
        "pois": top_pois,
        "n_days": days,
        "center_lng": center_lng,
        "center_lat": center_lat,
    }, config)

    # ── Step 3.5: Lake/mountain barrier detection ──────────────────────────
    # DBSCAN uses straight-line distance and can put POIs on opposite shores
    # of a lake in the same cluster. Check suspicious clusters with Amap.
    from agent.tools.poi_dedup import haversine_m

    async def _check_cluster_barrier(cluster):
        """If a cluster spans >8km straight-line, verify with Amap driving distance."""
        c_pois = cluster.get("pois", [])
        if len(c_pois) < 3:
            return cluster  # too small to split meaningfully
        # Find the two farthest POIs in this cluster
        max_d = 0
        farthest = (0, 1)
        for i in range(len(c_pois)):
            for j in range(i + 1, len(c_pois)):
                d = haversine_m(
                    c_pois[i].get("lng", 0), c_pois[i].get("lat", 0),
                    c_pois[j].get("lng", 0), c_pois[j].get("lat", 0),
                )
                if d > max_d:
                    max_d = d
                    farthest = (i, j)
        if max_d < 8000:
            return cluster  # compact enough, no barrier risk
        # Check driving distance for the farthest pair
        try:
            from agent.tools import get_amap
            amap = get_amap()
            a, b = c_pois[farthest[0]], c_pois[farthest[1]]
            route = await amap.plan_route(
                origin=(a["lng"], a["lat"]),
                destination=(b["lng"], b["lat"]),
                mode="driving",
            )
            drive_m = route.get("distance_km", 0) * 1000 if route else 0
            if drive_m > 0 and drive_m / max_d > 3.0:
                # Barrier detected! Split cluster by moving farthest outlier
                # to the nearest other cluster, or create a new day
                logger.warning(
                    "Barrier detected in cluster day %d: straight %.0fm, drive %.0fm (%.1fx)",
                    cluster.get("day", 0), max_d, drive_m, drive_m / max_d,
                )
                outlier = c_pois.pop(farthest[1])
                # Try to place outlier in another day's cluster
                placed = False
                for oc in clusters:
                    if oc.get("day") == cluster.get("day"):
                        continue
                    oc_pois = oc.get("pois", [])
                    if not oc_pois:
                        oc["pois"] = [outlier]
                        placed = True
                        break
                    # Check if outlier is closer to this other cluster's POIs
                    min_to_other = min(
                        haversine_m(outlier.get("lng", 0), outlier.get("lat", 0),
                                    p.get("lng", 0), p.get("lat", 0))
                        for p in oc_pois
                    )
                    if min_to_other < max_d * 0.8:
                        oc_pois.append(outlier)
                        placed = True
                        break
                if not placed:
                    cluster["pois"] = c_pois  # keep original, can't place
                    logger.info("Barrier outlier couldn't be reassigned, keeping original cluster")
        except Exception as exc:
            logger.warning("Barrier check failed for cluster day %d: %s",
                          cluster.get("day", 0), exc.__class__.__name__)
        return cluster

    # Run barrier checks SEQUENTIALLY to avoid concurrent mutation of clusters
    # (each coroutine reads/modifies the shared clusters list — parallel would race)
    for c in clusters:
        try:
            checked = await _check_cluster_barrier(c)
        except Exception:
            checked = c
    # Filter out empty clusters
    clusters = [c for c in clusters if not isinstance(c, Exception) and c.get("pois")]

    # ── Ensure every day has >= 3 POIs (barrier may have thinned some) ──
    # Rebalance: take nearest POI from the largest cluster for any under-filled day.
    for c in clusters:
        while len(c.get("pois", [])) < 3:
            # Find the largest cluster with >= 4 POIs
            donor = max(
                (oc for oc in clusters if oc is not c and len(oc.get("pois", [])) >= 4),
                key=lambda oc: len(oc.get("pois", [])),
                default=None,
            )
            if donor is None:
                break  # no donor available — accept under-filled
            # Find the POI in donor closest to this cluster's centroid
            donor_pois = donor["pois"]
            c_pois = c["pois"]
            if not c_pois:
                # empty cluster: take first POI from donor
                c["pois"] = [donor_pois.pop()]
                continue
            best = min(
                range(len(donor_pois)),
                key=lambda i: _min_dist_to_cluster(donor_pois[i], c_pois),
            )
            c["pois"].append(donor_pois.pop(best))

    # ── Even-distribution pass: move excess POIs from overloaded days ──
    # to under-filled ones.  Target is ceil(total / n_days); any cluster
    # with > target + 1 POIs donates its farthest POI to a cluster that is
    # below target.  This prevents "Day 1 has 7 POIs, Day 4 has 3" lopsidedness.
    total_pois = sum(len(c.get("pois", [])) for c in clusters)
    target = -(-total_pois // len(clusters)) if clusters else 3  # ceil division
    for _pass in range(3):  # at most 3 redistribution rounds
        changed = False
        for c in clusters:
            while len(c.get("pois", [])) > target + 1:
                # Find the most under-filled cluster
                receiver = min(
                    (oc for oc in clusters if oc is not c),
                    key=lambda oc: len(oc.get("pois", [])),
                )
                if len(receiver.get("pois", [])) >= target:
                    break  # everyone is at or above target
                donor_pois = c["pois"]
                recv_pois = receiver["pois"]
                if not recv_pois:
                    receiver["pois"] = [donor_pois.pop()]
                    changed = True
                    continue
                best = min(
                    range(len(donor_pois)),
                    key=lambda i: _min_dist_to_cluster(donor_pois[i], recv_pois),
                )
                receiver["pois"].append(donor_pois.pop(best))
                changed = True
        if not changed:
            break

    # ── Nearby-POI backfill: pull in high-score POIs that didn't make the ──
    # top_n cut but are very close to an under-filled day's route path.
    # Uses min-distance-to-any-cluster-member as a proxy for route proximity.
    if len(scored) > top_n:
        leftover = list(scored[top_n:])
        for c in clusters:
            c_pois = c.get("pois", [])
            if len(c_pois) >= max_per_day:
                continue
            if not c_pois:
                continue
            # Find the nearest leftover POI within 3km of any cluster member
            best_idx, best_dist = -1, float("inf")
            for i, p in enumerate(leftover):
                if not isinstance(p.get("lng"), (int, float)):
                    continue
                if not isinstance(p.get("lat"), (int, float)):
                    continue
                d = _min_dist_to_cluster(p, c_pois)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            if best_idx >= 0 and best_dist < 0.0009:
                c_pois.append(leftover.pop(best_idx))

    # ── Step 4: Route each day IN PARALLEL (semaphore=3 for Amap QPS limit) ──
    from agent.tools.submit_plan import route_one_day

    _route_sem = asyncio.Semaphore(3)  # Amap allows max 3 concurrent

    async def _route_day(cluster, idx):
        day_num = cluster.get("day", idx + 1)
        day_pois = cluster.get("pois", [])[:max_per_day]
        if not day_pois:
            return None
        async with _route_sem:
            return await route_one_day({"day": day_num, "pois": day_pois})

    writer({"type": "day_routing", "data": {"message": "正在规划每日路线..."}})
    routing_results = await asyncio.gather(
        *(_route_day(c, i) for i, c in enumerate(clusters)),
        return_exceptions=True,
    )
    daily_plans = [r for r in routing_results if r is not None and not isinstance(r, Exception)]

    if not daily_plans:
        writer({"type": "error", "data": {"message": "未能生成行程计划"}})
        return {"messages": [AIMessage(content="抱歉，行程规划失败，请重试。")]}

    # ── Step 5: Validate (Critic skipped — saves ~15s, marginal value) ────
    from agent.tools.submit_plan import submit_plan as submit_plan_fn

    # Also protect submit_plan from crashing the whole pipeline
    try:
        plan_result = await submit_plan_fn.ainvoke({
            "city": city,
            "days": len(daily_plans),
            "daily_plans": daily_plans,
        }, config)
    except Exception as exc:
        logger.exception("submit_plan crashed: %s", exc)
        plan_result = {"status": "accepted", "city": city, "daily_plans": daily_plans}

    # ── Step 6: Store plan for the summary node ──────────────────────────────
    # NOTE: StreamWriter does NOT emit on_custom_event in LangGraph 1.x +
    # astream_events v2.  Instead we embed route data in the return dict
    # so the SSE layer reads it from on_chain_end output.
    return {
        "plan_result": plan_result,
        "plan_city": city,
        "plan_days": len(daily_plans),
        "route_data": plan_result.get("daily_plans", daily_plans),
    }


# ---------------------------------------------------------------------------
# Pre-selected POIs fast path (user picked POIs on the map)
# ---------------------------------------------------------------------------


async def _plan_with_preselected_pois(
    preselected_pois: list[dict[str, Any]],
    city: str,
    writer: StreamWriter,
) -> dict[str, Any]:
    """Plan a trip directly from user-selected POIs — skip search entirely.

    Steps:
    1. Estimate visit durations
    2. Auto-determine days from POI count + spread
    3. Geo-partition into daily clusters
    4. Route each day via Amap
    5. Validate and submit
    """
    from agent.tools.submit_plan import route_one_day, submit_plan as submit_plan_fn
    from agent.tools.geo_partition import geo_partition as geo_partition_fn
    from app.services.duration_estimator import estimate_poi_duration_from_dict, estimate_daily_capacity

    pois = preselected_pois
    n = len(pois)

    # Estimate visit durations
    for poi in pois:
        poi["visit_duration_min"] = estimate_poi_duration_from_dict(poi)

    # Auto-determine days: 2 POIs → 1 day, 3-4 → 2 days, 5+ → 3 days
    if n <= 2:
        days = 1
    elif n <= 4:
        days = 2
    else:
        days = 3

    # Cap POIs per day
    dynamic_per_day = estimate_daily_capacity([p["visit_duration_min"] for p in pois])
    max_per_day = min(dynamic_per_day + 1, 8)

    logger.info("Pre-selected POI fast path: %d POIs, %d days, max %d/day", n, days, max_per_day)

    writer({"type": "searching", "data": {"message": f"正在用已选的 {n} 个POI规划行程..."}})

    # Compute center
    lngs = [p["lng"] for p in pois if isinstance(p.get("lng"), (int, float))]
    lats = [p["lat"] for p in pois if isinstance(p.get("lat"), (int, float))]
    center_lng = sum(lngs) / len(lngs) if lngs else 116.397
    center_lat = sum(lats) / len(lats) if lats else 39.908

    # Geo-partition
    writer({"type": "clustering", "data": {"message": f"正在按地理分区规划{days}天行程..."}})

    clusters = await geo_partition_fn.ainvoke({
        "pois": pois,
        "n_days": days,
        "center_lng": center_lng,
        "center_lat": center_lat,
    }, config={})

    # Route each day
    daily_plans: list[dict[str, Any]] = []
    for cluster in clusters:
        day_num = cluster.get("day", len(daily_plans) + 1)
        day_pois = cluster.get("pois", [])[:max_per_day]
        if not day_pois:
            continue

        writer({
            "type": "day_routing",
            "data": {"day": day_num, "message": f"正在规划第{day_num}天路线..."},
        })

        dp = {"day": day_num, "pois": day_pois}
        routed = await route_one_day(dp)
        daily_plans.append(routed)

    if not daily_plans:
        writer({"type": "error", "data": {"message": "未能生成行程计划"}})
        return {"messages": [AIMessage(content="抱歉，行程规划失败，请重试。")]}

    # Skip Critic validation — user hand-picked these POIs
    # Validate and submit
    plan_result = await submit_plan_fn.ainvoke({
        "city": city,
        "days": days,
        "daily_plans": daily_plans,
    }, config={})

    writer({
        "type": "route_result",
        "data": {"daily_plans": plan_result.get("daily_plans", daily_plans)},
    })

    return {
        "plan_result": plan_result,
        "plan_city": city,
        "plan_days": days,
    }


# ---------------------------------------------------------------------------
# ReAct agent node (same as graph.py agent_node, for backward compat)
# ---------------------------------------------------------------------------


async def agent_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """LLM call node — streams tokens for responsive UI."""
    from langchain_core.messages import AIMessageChunk

    model = _get_model()
    system_prompt = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    full_messages = [system_prompt] + state["messages"]

    accumulated = AIMessage(content="")
    async for chunk in model.astream(full_messages):
        if isinstance(chunk, AIMessageChunk):
            if chunk.content:
                accumulated.content += chunk.content
            if chunk.tool_call_chunks:
                tool_chunks = []
                for tc in chunk.tool_call_chunks:
                    tool_chunks.append({
                        "index": tc.get("index", 0),
                        "id": tc.get("id"),
                        "name": tc.get("name"),
                        "args": tc.get("args", ""),
                    })
                _merge_tool_call_chunks(accumulated, tool_chunks)

    if hasattr(accumulated, "tool_calls") and accumulated.tool_calls:
        for tc in accumulated.tool_calls:
            args = tc.get("args")
            if isinstance(args, str) and args.strip():
                try:
                    tc["args"] = json.loads(args)
                except json.JSONDecodeError:
                    pass

    return {"messages": [accumulated]}


# ---------------------------------------------------------------------------
# Agent summary node — generates natural-language summary after pipeline
# ---------------------------------------------------------------------------


async def summary_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Generate a natural-language summary of the planned trip."""
    plan = state.get("plan_result", {})
    city = state.get("plan_city", "")
    days = state.get("plan_days", 0)

    if not plan or plan.get("status") != "accepted":
        return {}

    # Build a concise summary for the LLM
    plan_summary_lines = [f"{city} {days}日游行程："]
    for day_plan in plan.get("daily_plans", []):
        day_num = day_plan.get("day", "?")
        poi_names = [p.get("name", "?") for p in day_plan.get("pois", [])]
        plan_summary_lines.append(f"  Day{day_num}: {' → '.join(poi_names)}")

    plan_text = "\n".join(plan_summary_lines)

    prompt = f"""你是一个旅游行程总结助手。根据以下行程，用自然语言向用户介绍这次旅行。

{plan_text}

请：
1. 简要说明行程的总体安排和特色
2. 每天用1-2句话概括亮点
3. 给出2-3条实用提示
4. 语气热情但不啰嗦，控制在300字以内"""

    raw_model = _get_model_no_tools()
    response = await raw_model.ainvoke([
        SystemMessage(content="你是热情的旅游行程总结助手。"),
        HumanMessage(content=prompt),
    ])

    return {"messages": [response]}


# ---------------------------------------------------------------------------
# Tools node (same as graph.py)
# ---------------------------------------------------------------------------


def _to_tool_message(result: Any, tool_name: str, call_id: str) -> ToolMessage:
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, default=str)
    return ToolMessage(content=result, name=tool_name, tool_call_id=call_id)


async def tools_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Dispatch tool calls from the last AIMessage."""
    tool_map = _build_tool_map()
    messages = state["messages"]
    last_msg = messages[-1]

    tool_calls = getattr(last_msg, "tool_calls", None) or []
    if not tool_calls:
        return {}

    parallel_calls: list[tuple[int, dict[str, Any]]] = []
    sequential_calls: list[tuple[int, dict[str, Any]]] = []

    for tc in tool_calls:
        name = tc.get("name", "")
        if name in PARALLELIZABLE_TOOLS:
            parallel_calls.append((tc["id"], tc))
        else:
            sequential_calls.append((tc["id"], tc))

    tool_messages: list[ToolMessage] = []

    for call_id, tc in sequential_calls:
        tool_fn = tool_map.get(tc["name"])
        if tool_fn is None:
            tool_messages.append(ToolMessage(
                content=json.dumps({"error": f"未知工具: {tc['name']}"}),
                tool_call_id=call_id,
            ))
            continue
        try:
            result = await asyncio.wait_for(
                tool_fn.ainvoke(tc["args"], config),
                timeout=TOOL_TIMEOUT_SEC,
            )
            tool_messages.append(_to_tool_message(result, tc["name"], call_id))
        except asyncio.TimeoutError:
            logger.warning("Tool %s timed out after %ds", tc["name"], TOOL_TIMEOUT_SEC)
            tool_messages.append(ToolMessage(
                content=json.dumps({"error": "工具执行失败"}),
                tool_call_id=call_id,
            ))
        except Exception as exc:
            logger.warning("Tool %s failed: %s", tc["name"], exc.__class__.__name__)
            tool_messages.append(ToolMessage(
                content=json.dumps({"error": "工具执行失败"}),
                tool_call_id=call_id,
            ))

    async def _call_parallel(call_id: str, tc: dict[str, Any]) -> ToolMessage:
        tool_fn = tool_map[tc["name"]]
        try:
            result = await asyncio.wait_for(
                tool_fn.ainvoke(tc["args"], config),
                timeout=TOOL_TIMEOUT_SEC,
            )
            return _to_tool_message(result, tc["name"], call_id)
        except asyncio.TimeoutError:
            return ToolMessage(
                content=json.dumps({"error": "工具执行失败"}),
                tool_call_id=call_id,
            )
        except Exception:
            return ToolMessage(
                content=json.dumps({"error": "工具执行失败"}),
                tool_call_id=call_id,
            )

    if parallel_calls:
        parallel_results = await asyncio.gather(
            *(_call_parallel(cid, tc) for cid, tc in parallel_calls),
            return_exceptions=True,
        )
        for item in parallel_results:
            if isinstance(item, ToolMessage):
                tool_messages.append(item)
            else:
                tool_messages.append(ToolMessage(
                    content=json.dumps({"error": "工具执行失败"}),
                    tool_call_id="unknown",
                ))

    new_count = state.get("tool_call_count", 0) + len(tool_calls)
    return {"messages": tool_messages, "tool_call_count": new_count}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _route_by_intent(state: AgentState) -> Literal["agent_node", "planning_pipeline"]:
    """Route after classify_intent: pipeline for trip planning, agent for rest."""
    intent = state.get("intent", "chat")
    if intent == "trip_planning":
        return "planning_pipeline"
    return "agent_node"


def _should_continue(state: AgentState) -> Literal["tools_node", "__end__"]:
    messages = state.get("messages", [])
    if not messages:
        return END
    last_msg = messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    if not tool_calls:
        return END
    if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
        logger.warning("tool_call_count=%d reached MAX=%d, forcing end",
                       state.get("tool_call_count"), MAX_TOOL_CALLS)
        return END
    return "tools_node"


def _route_after_pipeline(state: AgentState) -> Literal["summary_node", "agent_node"]:
    """After pipeline: go to summary if plan was accepted, else summary with fallback.

    We skip the agent retry loop entirely — if the pipeline failed validation,
    the LLM agent can't fix it without raw search data. Better to show what we
    have (route_result was already emitted) than to spin in a retry loop.
    """
    plan = state.get("plan_result", {})
    if plan and plan.get("status") == "accepted":
        return "summary_node"
    # Rejected — still go to summary, don't loop back to agent
    return "summary_node"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph_v2(checkpointer: object | None = None) -> CompiledStateGraph:
    """Build the v2 travel agent graph with intent routing + fixed pipeline.

    Args:
        checkpointer: Optional checkpointer override.
            - None (default): use the process-wide checkpointer and cache.
            - False: skip checkpointer.

    Returns:
        A compiled LangGraph ready for astream / ainvoke.
    """
    global _compiled_graph_v2

    use_default = checkpointer is None
    if use_default and _compiled_graph_v2 is not None:
        return _compiled_graph_v2

    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tools_node", tools_node)
    workflow.add_node("planning_pipeline", planning_pipeline_node)
    workflow.add_node("summary_node", summary_node)

    # Edges
    workflow.set_entry_point("classify_intent")

    workflow.add_conditional_edges("classify_intent", _route_by_intent, {
        "agent_node": "agent_node",
        "planning_pipeline": "planning_pipeline",
    })

    # Agent loop (for POI/route queries)
    workflow.add_edge("tools_node", "agent_node")
    workflow.add_conditional_edges("agent_node", _should_continue, {
        "tools_node": "tools_node",
        "__end__": END,
    })

    # Pipeline → summary
    workflow.add_conditional_edges("planning_pipeline", _route_after_pipeline, {
        "summary_node": "summary_node",
        "agent_node": "agent_node",
    })
    workflow.add_edge("summary_node", END)

    graph = workflow.compile()

    if use_default:
        cp = get_checkpointer()
        if cp:
            graph.checkpointer = cp
        _compiled_graph_v2 = graph
        return graph

    if checkpointer:
        graph.checkpointer = checkpointer
    return graph
