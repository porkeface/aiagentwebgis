"""Agent Chat SSE API endpoint.

POST /api/v1/agent/chat — Accepts ChatRequest, returns SSE stream of events.
Powered by a custom ReAct StateGraph with per-token text streaming and
per-tool progress events.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from langchain_core.messages import ToolMessage
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph_v2 import build_graph_v2
from agent.progress import ProgressTracker
from app.database import get_session
from app.models.user import User
from app.schemas.agent import ChatRequest
from app.services.auth_service import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Overall graph execution timeout — 5 minutes hard cap
GRAPH_EXECUTION_TIMEOUT = 300


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_session),
) -> Optional[int]:
    """Extract user from token if present, allow anonymous if not."""
    if not token:
        return None
    try:
        user_id = decode_token(token)
        if user_id is None:
            return None
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return user_id
    except (JWTError, ValueError, TypeError, SQLAlchemyError) as e:
        logger.warning("Optional auth token decode failed: %s", e)
        return None


def _format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _format_error_event(message: str) -> str:
    """Format an error SSE event."""
    return _format_sse_event(
        "message",
        {"type": "error", "data": {"message": message}},
    )


# ---------------------------------------------------------------------------
# POI lookup helpers — resolve poi_id references to full POI dicts
# ---------------------------------------------------------------------------


class POIRegistry:
    """Collects POI data from search tools and resolves poi_id for route_result."""

    def __init__(self) -> None:
        self._pois: dict[str, dict[str, Any]] = {}

    def ingest(self, pois: list[dict[str, Any]]) -> None:
        """Add POIs from a search result."""
        for poi in pois:
            pid = str(poi.get("id") or poi.get("amap_id", ""))
            if pid:
                self._pois[pid] = poi

    def ingest_route_pois(self, ordered_pois: list[dict[str, Any]]) -> None:
        """Ingest POI name/coordinates from plan_day_route ordered_pois output."""
        for p in ordered_pois:
            pid = str(p.get("id") or p.get("poi_id", ""))
            if pid and pid not in self._pois:
                self._pois[pid] = {
                    "id": pid,
                    "name": p.get("name", pid),
                    "lng": p.get("lng", 0),
                    "lat": p.get("lat", 0),
                    "category": p.get("category", ""),
                }

    def resolve(self, poi_id: str) -> dict[str, Any] | None:
        """Look up a POI by id."""
        return self._pois.get(str(poi_id))

    def all_pois(self) -> list[dict[str, Any]]:
        """Return all known POIs as a list."""
        return list(self._pois.values())

    def any(self) -> bool:
        return bool(self._pois)


def _build_poi_result_event(registry: POIRegistry) -> str | None:
    """Build a poi_result SSE event from the current registry."""
    pois = registry.all_pois()
    if not pois:
        return None

    valid = [
        p for p in pois
        if isinstance(p.get("lng"), (int, float)) and isinstance(p.get("lat"), (int, float))
    ]
    if not valid:
        return None

    center_lng = sum(p["lng"] for p in valid) / len(valid)
    center_lat = sum(p["lat"] for p in valid) / len(valid)

    payload = [
        {
            "id": p.get("id", 0),
            "name": p.get("name", ""),
            "category": p.get("category", ""),
            "address": p.get("address"),
            "city": p.get("city"),
            "lng": p.get("lng", 0.0),
            "lat": p.get("lat", 0.0),
            "rating": p.get("rating"),
            "review_count": p.get("review_count"),
            "tags": p.get("tags", []),
            "photo": p.get("photo"),
            "description": p.get("description"),
        }
        for p in valid
    ]

    return _format_sse_event("message", {
        "type": "poi_result",
        "data": {
            "pois": payload,
            "center": {"lng": center_lng, "lat": center_lat},
            "zoom": 12,
        },
    })


def _build_route_result_event(
    plan_output: dict[str, Any],
    registry: POIRegistry,
) -> str | None:
    """Build a route_result SSE event from submit_plan output."""
    if plan_output.get("status") != "accepted":
        return None

    daily_plans_raw = plan_output.get("daily_plans", [])
    if not daily_plans_raw:
        return None

    formatted_plans: list[dict[str, Any]] = []

    for day_plan in daily_plans_raw:
        day_pois: list[dict[str, Any]] = []
        for ref in day_plan.get("pois", []):
            pid = str(ref.get("poi_id", ""))
            full = registry.resolve(pid)
            if full is None:
                ref_lng = ref.get("lng", 0.0)
                ref_lat = ref.get("lat", 0.0)
                day_pois.append({
                    "id": pid,
                    "name": ref.get("name", f"POI {pid[:8]}"),
                    "category": ref.get("category", ""),
                    "lng": float(ref_lng) if ref_lng else 0.0,
                    "lat": float(ref_lat) if ref_lat else 0.0,
                    "time_slot": ref.get("time_slot"),
                    "visit_duration_min": ref.get("visit_duration_min"),
                    "meal_type": ref.get("meal_type"),
                })
                continue
            day_pois.append({
                "id": full.get("id", pid),
                "name": full.get("name", ""),
                "category": full.get("category", ""),
                "address": full.get("address"),
                "lng": full.get("lng", 0.0),
                "lat": full.get("lat", 0.0),
                "rating": full.get("rating"),
                "tags": full.get("tags", []),
                "score": full.get("score", 0),
                "photo": full.get("photo"),
                "description": full.get("description"),
                "time_slot": ref.get("time_slot"),
                "visit_duration_min": ref.get("visit_duration_min"),
                "meal_type": ref.get("meal_type"),
            })

        # Polyline/segments now come from submit_plan directly (auto-routed)
        formatted_plans.append({
            "day": day_plan.get("day", 1),
            "day_title": day_plan.get("day_theme", f"第{day_plan.get('day', 1)}天"),
            "pois": day_pois,
            "total_distance_km": day_plan.get("total_distance_km", 0),
            "total_duration_min": day_plan.get("total_duration_min", 0),
            "total_transit_min": day_plan.get("total_transit_min", 0),
            "polyline": day_plan.get("polyline", ""),
            "segments": day_plan.get("segments", []),
        })

    return _format_sse_event("message", {
        "type": "route_result",
        "data": {"daily_plans": formatted_plans},
    })


def _build_plan_summary_event(plan_output: dict[str, Any]) -> str | None:
    """Build a plan_summary SSE event."""
    city = plan_output.get("city")
    days = plan_output.get("days")
    if not city or not days:
        return None
    return _format_sse_event("message", {
        "type": "plan_summary",
        "data": {"city": city, "days": days},
    })


def _build_route_result_from_pipeline(
    pipeline_data: dict[str, Any],
    registry: POIRegistry,
) -> str | None:
    """Build a route_result SSE event from planning pipeline output."""
    daily_plans_raw = pipeline_data.get("daily_plans", [])
    if not daily_plans_raw:
        return None

    formatted_plans: list[dict[str, Any]] = []
    for day_plan in daily_plans_raw:
        day_pois: list[dict[str, Any]] = []
        for ref in day_plan.get("pois", []):
            if isinstance(ref, str):
                # String POI id — use as-is
                day_pois.append({"id": ref, "name": ref, "lng": 0.0, "lat": 0.0, "category": ""})
                continue
            pid = str(ref.get("poi_id", ref.get("id", "")))
            full = registry.resolve(pid)
            if full is None:
                ref_lng = ref.get("lng", 0.0)
                ref_lat = ref.get("lat", 0.0)
                day_pois.append({
                    "id": pid,
                    "name": ref.get("name", f"POI {pid[:8]}"),
                    "category": ref.get("category", ""),
                    "lng": float(ref_lng) if ref_lng else 0.0,
                    "lat": float(ref_lat) if ref_lat else 0.0,
                    "time_slot": ref.get("time_slot"),
                    "visit_duration_min": ref.get("visit_duration_min"),
                    "meal_type": ref.get("meal_type"),
                })
                continue
            day_pois.append({
                "id": full.get("id", pid),
                "name": full.get("name", ""),
                "category": full.get("category", ""),
                "address": full.get("address"),
                "lng": full.get("lng", 0.0),
                "lat": full.get("lat", 0.0),
                "rating": full.get("rating"),
                "tags": full.get("tags", []),
                "photo": full.get("photo"),
                "description": full.get("description"),
                "time_slot": ref.get("time_slot"),
                "visit_duration_min": ref.get("visit_duration_min"),
                "meal_type": ref.get("meal_type"),
            })

        formatted_plans.append({
            "day": day_plan.get("day", 1),
            "day_title": day_plan.get("day_theme", f"第{day_plan.get('day', 1)}天"),
            "pois": day_pois,
            "total_distance_km": day_plan.get("total_distance_km", 0),
            "total_duration_min": day_plan.get("total_duration_min", 0),
            "total_transit_min": day_plan.get("total_transit_min", 0),
            "polyline": day_plan.get("polyline", ""),
            "segments": day_plan.get("segments", []),
        })

    return _format_sse_event("message", {
        "type": "route_result",
        "data": {"daily_plans": formatted_plans},
    })


# ---------------------------------------------------------------------------
# Tool result handler (extracted from inline on_tool_end logic)
# ---------------------------------------------------------------------------


def _handle_tool_result(
    tool_name: str,
    output: Any,
    registry: POIRegistry,
    map_snapshot: dict[str, Any],
) -> str | None:
    """Handle a single tool result — emit poi_result, ingest coords, etc.

    Returns an SSE event string if one should be yielded, or None.
    """
    # Unwrap ToolMessage wrapper
    if isinstance(output, ToolMessage):
        content = output.content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass
        output = content

    # search_pois / search_nearby → accumulate + emit poi_result
    if tool_name in ("search_pois", "search_nearby"):
        if isinstance(output, list):
            registry.ingest(output)
        event_str = _build_poi_result_event(registry)
        if event_str:
            parsed = json.loads(event_str.split("\n")[1].replace("data: ", "", 1))
            map_snapshot["pois"] = parsed.get("data", {}).get("pois", [])
        return event_str

    # plan_route → emit single route for map display
    if tool_name == "plan_route":
        if isinstance(output, dict) and output.get("polyline"):
            origin_name = output.get("origin_name", "起点")
            dest_name = output.get("dest_name", "终点")
            origin_lng = output.get("origin_lng", 0) or 0
            origin_lat = output.get("origin_lat", 0) or 0
            dest_lng = output.get("dest_lng", 0) or 0
            dest_lat = output.get("dest_lat", 0) or 0
            ev = {
                "type": "route_result",
                "data": {"daily_plans": [{
                    "day": 1,
                    "day_title": output.get("route_name", f"{origin_name} → {dest_name}"),
                    "pois": [
                        {"id": "plan_route_origin", "name": origin_name,
                         "lng": origin_lng, "lat": origin_lat,
                         "category": ""},
                        {"id": "plan_route_dest", "name": dest_name,
                         "lng": dest_lng, "lat": dest_lat,
                         "category": ""},
                    ],
                    "total_distance_km": output.get("distance_km", 0),
                    "total_transit_min": output.get("duration_min", 0),
                    "polyline": output.get("polyline", ""),
                    "segments": output.get("segments", []),
                }]},
            }
            ev_str = _format_sse_event("message", ev)
            parsed = json.loads(ev_str.split("\n")[1].replace("data: ", "", 1))
            map_snapshot["routes"] = parsed.get("data", {}).get("daily_plans", [])
            return ev_str
        return None

    # submit_plan → route_result + plan_summary
    if tool_name == "submit_plan":
        if isinstance(output, dict) and output.get("status") == "accepted":
            route = _build_route_result_event(output, registry)
            if route:
                parsed = json.loads(route.split("\n")[1].replace("data: ", "", 1))
                map_snapshot["routes"] = parsed.get("data", {}).get("daily_plans", [])
            summary = _build_plan_summary_event(output)
            if summary:
                p = json.loads(summary.split("\n")[1].replace("data: ", "", 1))
                map_snapshot["plan_summary"] = p.get("data", {})
            # Return route event (caller yields it); summary is yielded separately
            return route
        return None

    return None


# ---------------------------------------------------------------------------
# Event generator
# ---------------------------------------------------------------------------


async def _event_generator(
    session_id: str,
    message: str,
    user_id: int | None = None,
    http_request: Request | None = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from the custom ReAct StateGraph.

    Uses ``astream(stream_mode="updates")`` — each node's output is yielded
    as a dict of {node_name: node_output}.  The API layer extracts AIMessages
    (LLM text + tool_calls) and ToolMessages (tool results) from updates.
    """
    map_snapshot: dict[str, Any] = {"pois": [], "routes": [], "plan_summary": None}
    messages_for_db: list[dict[str, Any]] | None = None

    # Stash the original task so we can cancel the agent loop when the
    # client hangs up.  asyncio.current_task() is None outside a running loop.
    current_task = asyncio.current_task()

    async def _client_gone() -> bool:
        """Return True if the HTTP client has disconnected."""
        if http_request is None:
            return False
        try:
            return await http_request.is_disconnected()
        except Exception:
            return True

    # Background watcher: polls for client disconnect every 1s while astream
    # is awaiting the next event.  The per-event check inside the async-for
    # only fires when a node yields a chunk — if a long-running LLM call
    # has no intermediate events for many seconds, we'd otherwise miss a
    # disconnect until the next chunk arrives.  A 1s tick is cheap and
    # shrinks the worst-case abort latency from "end of current step" to
    # ~1s.
    client_disconnected = asyncio.Event()
    _watcher_task: asyncio.Task[None] | None = None
    if http_request is not None and current_task is not None:
        async def _watch_disconnect() -> None:
            while not client_disconnected.is_set():
                if await _client_gone():
                    client_disconnected.set()
                    if current_task is not None and not current_task.done():
                        current_task.cancel()
                    return
                try:
                    await asyncio.sleep(1.0)
                except asyncio.CancelledError:
                    return

        _watcher_task = asyncio.create_task(_watch_disconnect())

    try:
        # Trip planning does not need checkpointing — each request is
        # self-contained. The pipeline path goes classify_intent →
        # planning_pipeline → summary_node → END, which never loops
        # back, so the checkpointer only gets in the way by merging
        # old graph state into future runs.
        graph = build_graph_v2(checkpointer=False)
        config: dict[str, Any] = {
            "configurable": {"thread_id": session_id},
        }

        initial_state = {
            "messages": [{"role": "user", "content": message}],
            "tool_call_count": 0,
            "session_id": session_id,
        }

        registry = POIRegistry()
        progress = ProgressTracker()
        accumulated_text = ""

        # Use astream_events for per-token streaming + node-level updates.
        # Two layers of disconnect detection:
        #  1. Per-event check below — fires whenever a node yields a chunk.
        #  2. _watch_disconnect (started above) polls every 1s and cancels
        #     this task if the client hangs up during a long LLM call that
        #     hasn't emitted an event recently.
        try:
            async with asyncio.timeout(GRAPH_EXECUTION_TIMEOUT):
                async for event in graph.astream_events(initial_state, config, version="v2"):
                    if await _client_gone():
                        logger.info(
                            "SSE client disconnected mid-stream; aborting graph "
                            "for session_id=%s",
                            session_id,
                        )
                        if current_task is not None:
                            current_task.cancel()
                        return
                    kind = event.get("event", "")
                    name = event.get("name", "")
                    data = event.get("data", {})
    
                    # ── Custom writer events (from planning pipeline) ──
                    if kind == "on_custom_event":
                        custom_name = event.get("name", "")
                        custom_data = event.get("data", {})
    
                        if custom_name == "intent_detected":
                            # Also forward the intent data so the frontend can
                            # display the city/days that were extracted
                            yield _format_sse_event("message", {
                                "type": "intent_detected",
                                "data": {
                                    "content": "AI 正在分析您的需求...",
                                    "intent": custom_data.get("intent", "unknown"),
                                    "city": custom_data.get("city"),
                                    "days": custom_data.get("days"),
                                },
                            })
    
                        elif custom_name == "searching":
                            yield _format_sse_event("message", {
                                "type": "tool_calling",
                                "data": {"content": custom_data.get("message", "正在搜索...")},
                            })
    
                        elif custom_name == "candidates_ready":
                            pois = custom_data.get("pois", [])
                            registry.ingest(pois)
                            poi_event = _build_poi_result_event(registry)
                            if poi_event:
                                yield poi_event
    
                        elif custom_name == "scoring":
                            yield _format_sse_event("message", {
                                "type": "tool_calling",
                                "data": {"content": custom_data.get("message", "正在评估...")},
                            })
    
                        elif custom_name == "clustering":
                            yield _format_sse_event("message", {
                                "type": "tool_calling",
                                "data": {"content": custom_data.get("message", "正在分区...")},
                            })
    
                        elif custom_name == "day_routing":
                            day_num = custom_data.get("day", 0)
                            yield _format_sse_event("message", {
                                "type": "progress",
                                "data": {
                                    "step": day_num,
                                    "total": len(registry.all_pois()) or 3,
                                    "label": custom_data.get("message", f"正在规划第{day_num}天路线..."),
                                },
                            })
    
                        elif custom_name == "route_result":
                            route_event = _build_route_result_from_pipeline(custom_data, registry)
                            if route_event:
                                parsed = json.loads(route_event.split("\n")[1].replace("data: ", "", 1))
                                map_snapshot["routes"] = parsed.get("data", {}).get("daily_plans", [])
                                yield route_event
    
                        elif custom_name == "plan_summary":
                            plan_event = _format_sse_event("message", {
                                "type": "plan_summary",
                                "data": custom_data,
                            })
                            yield plan_event
                            p = custom_data
                            map_snapshot["plan_summary"] = p
    
                        elif custom_name == "error":
                            yield _format_sse_event("message", {
                                "type": "error",
                                "data": custom_data,
                            })
    
                    # ── Per-token text streaming ──
                    # Skip streaming from classify_intent node — its raw JSON
                    # output is not user-facing text and would pollute the chat.
                    elif kind == "on_chat_model_stream":
                        lg_node = event.get("metadata", {}).get("langgraph_node", "")
                        if lg_node != "classify_intent":
                            chunk = data.get("chunk")
                            if chunk and hasattr(chunk, "content") and chunk.content:
                                accumulated_text += chunk.content
                                yield _format_sse_event("message", {
                                    "type": "text",
                                    "data": {"content": chunk.content},
                                })
    
                    # ── Chain ends: pipeline emits route_result via return dict ──
                    elif kind == "on_chain_end" and name == "planning_pipeline":
                        output = data.get("output", {})
                        route_data = output.get("route_data", [])
                        if route_data:
                            route_event = _build_route_result_from_pipeline(
                                {"daily_plans": route_data}, registry
                            )
                            if route_event:
                                parsed = json.loads(route_event.split("\n")[1].replace("data: ", "", 1))
                                map_snapshot["routes"] = parsed.get("data", {}).get("daily_plans", [])
                                yield route_event
                        plan_summary = output.get("plan_result", {})
                        if plan_summary.get("status") == "accepted":
                            summary = _build_plan_summary_event(plan_summary)
                            if summary:
                                yield summary

                    # ── Chain starts ──
                    elif kind == "on_chain_start":
                        accumulated_text = ""
                        yield _format_sse_event("message", {
                            "type": "thinking",
                            "data": {"content": "AI 正在思考..."},
                        })
    
                    # ── Tool starts ──
                    elif kind == "on_tool_start":
                        tool_name = name or ""
                        tool_input = data.get("input", {})
                        label = progress.add_tool(tool_name, tool_input)
                        yield _format_sse_event("message", {
                            "type": "tool_calling",
                            "data": {"content": label},
                        })
    
                    # ── Tool ends ──
                    elif kind == "on_tool_end":
                        tool_name = name or ""
                        output = data.get("output")
    
                        # Unwrap ToolMessage
                        if hasattr(output, "content") and hasattr(output, "tool_call_id"):
                            output = output.content
                            if isinstance(output, str):
                                try: output = json.loads(output)
                                except (json.JSONDecodeError, TypeError): pass
    
                        progress.mark_complete()
                        ev = {
                            "type": "progress",
                            "data": {
                                "step": progress.completed,
                                "total": max(len(progress.labels), progress.completed),
                                "label": (progress.labels[progress.completed - 1] if progress.completed <= len(progress.labels) else "处理中..."),
                            },
                        }
                        yield _format_sse_event("message", ev)
    
                        result = _handle_tool_result(tool_name, output, registry, map_snapshot)
                        if result:
                            yield result
                        if tool_name == "submit_plan" and isinstance(output, dict) and output.get("status") == "accepted":
                            summary = _build_plan_summary_event(output)
                            if summary:
                                yield summary
        except TimeoutError:
            logger.error(f"Agent timeout for session_id={session_id}")
            yield _format_error_event("抱歉，AI 处理超时，请稍后重试。")
        except ConnectionError as e:
            logger.error(f"Agent connection error for session_id={session_id}: {e}")
            yield _format_error_event("抱歉，服务连接失败，请检查网络后重试。")
        except Exception as e:
            logger.exception(f"Agent unexpected error for session_id={session_id}")
            yield _format_error_event("抱歉，处理您的请求时出现错误，请稍后重试。")

        # ---- Build messages list for DB persistence ----
        messages_for_db = [
            {"role": "user", "content": message, "timestamp": _now_iso()},
        ]
        if accumulated_text.strip():
            messages_for_db.append(
                {"role": "assistant", "content": accumulated_text.strip(), "timestamp": _now_iso()},
            )

        # Capture final POI snapshot
        final_poi_event = _build_poi_result_event(registry)
        if final_poi_event:
            parsed = json.loads(final_poi_event.split("\n")[1].replace("data: ", "", 1))
            map_snapshot["pois"] = parsed.get("data", {}).get("pois", [])

    finally:
        # Always tear down the disconnect watcher — even on success, error,
        # or cancellation.  Setting the event first makes the watcher exit
        # its sleep on the next tick instead of waiting up to 1s.
        client_disconnected.set()
        if _watcher_task is not None and not _watcher_task.done():
            _watcher_task.cancel()
            try:
                await _watcher_task
            except (asyncio.CancelledError, Exception):
                pass
        if user_id is not None and messages_for_db is not None:
            try:
                from app.database import async_session_factory
                from app.services import chat_service

                async with async_session_factory() as db:
                    await chat_service.save_or_update_session(
                        db=db,
                        user_id=user_id,
                        thread_id=session_id,
                        messages=messages_for_db,
                        agent_state={"map_snapshot": map_snapshot},
                    )
                    await db.commit()
            except Exception:
                logger.exception("Failed to save chat session for user_id=%s", user_id)

    # Final done event
    yield _format_sse_event("done", {})


def _now_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    summary="Chat with AI travel agent",
    description="Send a message to the AI agent and receive SSE-streamed events.",
)
async def chat(
    request: ChatRequest,
    http_request: Request,
    user_id: Optional[int] = Depends(get_optional_user),
) -> StreamingResponse:
    """Agent chat endpoint with SSE streaming.

    The ReAct agent autonomously decides whether to search POIs, plan
    routes, or just chat.  SSE events (text, poi_result, route_result,
    plan_summary, tool_calling, progress, error, done) are streamed in real time.
    """
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _event_generator(session_id, request.message, user_id, http_request),
        media_type="text/event-stream",
    )
