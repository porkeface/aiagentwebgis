"""Agent chat Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for agent chat."""

    message: str
    session_id: str | None = None


class ChatSSEEvent(BaseModel):
    """SSE event schema for streaming agent responses."""

    type: Literal[
        "thinking",
        "tool_calling",
        "poi_result",
        "route_result",
        "plan_summary",
        "text",
        "error",
        "progress",
    ]
    data: dict = Field(default_factory=dict)
    content: str | None = None
