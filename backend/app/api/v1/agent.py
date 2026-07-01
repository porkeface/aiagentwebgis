"""Agent Chat SSE API endpoint.

POST /api/v1/agent/chat — Accepts ChatRequest, returns SSE stream of events.
Powered by LangGraph create_react_agent with astream_events.
"""

import json
import logging
import uuid
import asyncio
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph
from app.database import get_session
from app.models.user import User
from app.schemas.agent import ChatRequest
from app.services.auth_service import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


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
            # plan_day_route returns name not id — match by name if id missing
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
    """Build a route_result SSE event from submit_plan output.

    Resolves poi_id references to full POI dicts and builds the
    DailyPlan structure the frontend expects.
    """
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
                # POI not in registry (user-provided) — use ref fields with fallback
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

        formatted_plans.append({
            "day": day_plan.get("day", 1),
            "day_title": day_plan.get("day_theme", f"第{day_plan.get('day', 1)}天"),
            "pois": day_pois,
            "total_duration_min": day_plan.get("total_duration_min", 0),
            "total_transit_min": day_plan.get("total_transit_min", 0),
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


# ---------------------------------------------------------------------------
# Event generator
# ---------------------------------------------------------------------------


async def _event_generator(
    session_id: str,
    message: str,
    user_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from the ReAct agent's astream_events.

    When ``user_id`` is provided, the conversation + map snapshot are
    persisted to ``chat_sessions`` so the user can revisit past chats.

    Args:
        session_id: Unique session identifier (used as thread_id).
        message: User message content.
        user_id: Authenticated user id (None for anonymous).
    """
    map_snapshot: dict[str, Any] = {"pois": [], "routes": [], "plan_summary": None}
    messages_for_db: list[dict[str, Any]] | None = None

    try:
        graph = build_graph()
        config = {"configurable": {"thread_id": session_id}}

        initial_state = {
            "messages": [{"role": "user", "content": message}],
            "remaining_steps": 15,
        }

        registry = POIRegistry()
        accumulated_text = ""

        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            # ---- LLM starts thinking ----
            if kind == "on_chat_model_start":
                accumulated_text = ""
                yield _format_sse_event("message", {
                    "type": "thinking",
                    "data": {"content": "AI 正在思考..."},
                })

            # ---- LLM token stream ----
            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    accumulated_text += chunk.content
                    # Stream each chunk immediately for real-time display
                    yield _format_sse_event("message", {
                        "type": "text",
                        "data": {"content": chunk.content},
                    })

            # ---- LLM response complete (also streamed: drops duplicate) ----
            elif kind == "on_chat_model_end":
                # ChatOpenAI with streaming=True may still emit on_chat_model_end
                # with the full concatenated content. We only use it as a
                # fallback when streaming delivered nothing.
                output = data.get("output")
                if output and hasattr(output, "content") and output.content:
                    if not accumulated_text:
                        accumulated_text = output.content
                        yield _format_sse_event("message", {
                            "type": "text",
                            "data": {"content": output.content},
                        })

            # ---- Tool starts ----
            elif kind == "on_tool_start":
                tool_name = name or ""
                tool_input = data.get("input", {})

                label_map = {
                    "search_pois": f"正在搜索 {tool_input.get('city', '')} 的 {tool_input.get('category', '')}...",
                    "search_nearby": "正在搜索周边...",
                    "plan_route": "正在查询路线距离...",
                    "optimize_route": "正在优化访问顺序...",
                    "score_pois": "正在评估 POI...",
                    "submit_plan": "正在验证行程...",
                }
                label = label_map.get(tool_name, f"正在 {tool_name}...")

                yield _format_sse_event("message", {
                    "type": "tool_calling",
                    "data": {"content": label},
                })

            # ---- Tool ends ----
            elif kind == "on_tool_end":
                tool_name = name or ""
                output = data.get("output")

                # Unwrap LangChain ToolMessage wrapper (streaming=True path)
                if hasattr(output, "content") and hasattr(output, "tool_call_id"):
                    output = output.content
                    if isinstance(output, str):
                        try:
                            output = json.loads(output)
                        except (json.JSONDecodeError, TypeError):
                            pass

                # search_pois / search_nearby → accumulate POIs + emit poi_result
                if tool_name in ("search_pois", "search_nearby"):
                    if isinstance(output, list):
                        registry.ingest(output)
                    event_str = _build_poi_result_event(registry)
                    if event_str:
                        yield event_str
                        parsed = json.loads(event_str.split("\n")[1].replace("data: ", "", 1))
                        map_snapshot["pois"] = parsed.get("data", {}).get("pois", [])

                # plan_day_route → cache coordinates for submit_plan resolution
                elif tool_name == "plan_day_route":
                    if isinstance(output, dict):
                        ordered = output.get("ordered_pois", [])
                        if ordered:
                            registry.ingest_route_pois(ordered)

                # submit_plan → emit route_result + plan_summary
                elif tool_name == "submit_plan":
                    if isinstance(output, dict) and output.get("status") == "accepted":
                        route = _build_route_result_event(output, registry)
                        if route:
                            yield route
                            p = json.loads(route.split("\n")[1].replace("data: ", "", 1))
                            map_snapshot["routes"] = p.get("data", {}).get("daily_plans", [])
                        summary = _build_plan_summary_event(output)
                        if summary:
                            yield summary
                            p = json.loads(summary.split("\n")[1].replace("data: ", "", 1))
                            map_snapshot["plan_summary"] = p.get("data", {})

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

    except TimeoutError:
        logger.error(f"Agent timeout for session_id={session_id}")
        yield _format_error_event("抱歉，AI 处理超时，请稍后重试。")
    except ConnectionError as e:
        logger.error(f"Agent connection error for session_id={session_id}: {e}")
        yield _format_error_event("抱歉，服务连接失败，请检查网络后重试。")
    except Exception as e:
        logger.exception(f"Agent unexpected error for session_id={session_id}")
        yield _format_error_event(f"抱歉，处理您的请求时出现错误，请稍后重试。({type(e).__name__})")

    finally:
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
    from datetime import datetime, timezone
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
    user_id: Optional[int] = Depends(get_optional_user),
) -> StreamingResponse:
    """Agent chat endpoint with SSE streaming.

    The ReAct agent autonomously decides whether to search POIs, plan
    routes, or just chat.  SSE events (text, poi_result, route_result,
    plan_summary, tool_calling, error, done) are streamed in real time.
    """
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _event_generator(session_id, request.message, user_id),
        media_type="text/event-stream",
    )
