"""Agent Chat SSE API endpoint.

POST /api/v1/agent/chat - Accepts ChatRequest, returns SSE stream of events.
"""

import json
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.graph import build_graph
from app.schemas.agent import ChatRequest

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


def _format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event.

    Args:
        event_type: The SSE event type (e.g., 'message', 'done').
        data: The event data to serialize as JSON.

    Returns:
        Formatted SSE event string.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_generator(
    session_id: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from agent graph execution.

    Args:
        session_id: Unique session identifier.
        message: User message content.

    Yields:
        SSE-formatted event strings.
    """
    # Build graph and invoke with initial state
    graph = build_graph()
    initial_state = {
        "messages": [{"role": "user", "content": message}],
        "session_id": session_id,
    }
    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(initial_state, config=config)

    # Stream events from structured_plan
    structured_plan: list[dict[str, Any]] = result.get("structured_plan", [])

    for event in structured_plan:
        event_type = event.get("type", "text")
        # Wrap event data in standard envelope
        event_data = {"type": event_type, "data": event}
        yield _format_sse_event("message", event_data)

    # Final done event
    yield _format_sse_event("done", {})


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Agent chat endpoint with SSE streaming.

    Args:
        request: ChatRequest with session_id (optional) and message.

    Returns:
        StreamingResponse with text/event-stream content type.
    """
    session_id = request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _event_generator(session_id, request.message),
        media_type="text/event-stream",
    )
