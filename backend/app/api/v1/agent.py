"""Agent Chat SSE API endpoint.

POST /api/v1/agent/chat - Accepts ChatRequest, returns SSE stream of events.
Includes comprehensive error handling with friendly error messages.
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

# Optional auth - allows anonymous access for now
# TODO: H2 - Add rate limiting middleware to prevent abuse
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_session),
) -> Optional[int]:
    """Extract user from token if present, allow anonymous if not.

    Returns:
        User ID if authenticated, None if anonymous.
    """
    if not token:
        return None
    try:
        user_id = decode_token(token)
        if user_id is None:
            return None
        # Verify user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return user_id
    except (JWTError, ValueError, TypeError, SQLAlchemyError) as e:
        logger.warning("Optional auth token decode failed: %s", e)
        return None


def _format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event.

    Args:
        event_type: The SSE event type (e.g., 'message', 'done').
        data: The event data to serialize as JSON.

    Returns:
        Formatted SSE event string.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _format_error_event(message: str) -> str:
    """Format an error SSE event with user-friendly message.

    Args:
        message: Error message to display to the user.

    Returns:
        Formatted SSE error event string.
    """
    return _format_sse_event(
        "message",
        {
            "type": "error",
            "data": {"message": message},
        },
    )


async def _event_generator(
    session_id: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from agent graph execution.

    Handles errors gracefully and sends user-friendly error messages
    through the SSE stream instead of crashing.

    Args:
        session_id: Unique session identifier.
        message: User message content.

    Yields:
        SSE-formatted event strings.
    """
    try:
        # Build graph and invoke with initial state.
        # NOTE: AgentState has 15+ fields. Initial state must populate ALL of
        # them so LangGraph's input merge doesn't leave undefined keys; nodes
        # read via state.get(...) which is safe either way, but missing keys
        # would break any future input_schema validation and the checkpointer
        # replay path.
        graph = build_graph()
        initial_state = {
            "messages": [{"role": "user", "content": message}],
            "session_id": session_id,
            "intent": "",
            "city": None,
            "days": None,
            "preferences": [],
            "companion_types": [],
            "budget_level": None,
            "candidate_pois": [],
            "selected_pois": [],
            "daily_plans": [],
            "route_polylines": [],
            "recommendation_weights": None,
            "response_text": "",
            "structured_plan": None,
        }
        config = {"configurable": {"thread_id": session_id}}

        result = await asyncio.wait_for(
            graph.ainvoke(initial_state, config=config),
            timeout=120.0,
        )

        # Stream events from structured_plan.
        # Each event is an envelope on the wire: { type, data: {...payload} }.
        # The frontend SSE parser expects this shape (see frontend/src/api/agent.ts
        # parseSSEEvent). We pull `event.data` when present (the formatter emits
        # both flat and wrapped forms) and re-emit as a single envelope.
        structured_plan: list[dict[str, Any]] = result.get("structured_plan", [])

        for event in structured_plan:
            event_type = event.get("type", "message")
            payload = event.get("data", event)
            yield _format_sse_event("message", {"type": event_type, "data": payload})

    except TimeoutError:
        logger.error(f"Agent timeout for session_id={session_id}")
        yield _format_error_event("抱歉，AI 处理超时，请稍后重试。")
    except ConnectionError as e:
        logger.error(f"Agent connection error for session_id={session_id}: {e}")
        yield _format_error_event("抱歉，服务连接失败，请检查网络后重试。")
    except Exception as e:
        logger.error(f"Agent unexpected error for session_id={session_id}: {e}")
        yield _format_error_event("抱歉，处理您的请求时出现错误，请稍后重试。")

    # Final done event
    yield _format_sse_event("done", {})


@router.post(
    "/chat",
    summary="Chat with AI travel agent",
    description="Send a message to the AI agent and receive SSE-streamed events (thinking, tool_calling, poi_result, route_result, plan_summary, text, error, done).",
)
async def chat(
    request: ChatRequest,
    user_id: Optional[int] = Depends(get_optional_user),
) -> StreamingResponse:
    """Agent chat endpoint with SSE streaming.

    Args:
        request: ChatRequest with session_id (optional) and message.
        user_id: Optional authenticated user ID (None for anonymous).

    Returns:
        StreamingResponse with text/event-stream content type.
    """
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _event_generator(session_id, request.message),
        media_type="text/event-stream",
    )
