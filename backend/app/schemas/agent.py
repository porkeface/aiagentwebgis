"""Agent chat Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for agent chat."""

    # Cap message length to prevent a single request from draining the LLM
    # wallet: 4000 chars ≈ a normal-length travel request; longer inputs add
    # token cost without improving the model's planning accuracy.
    message: str = Field(min_length=1, max_length=4000)
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
        "intent_detected",
        "searching",
        "candidates_ready",
        "scoring",
        "clustering",
        "day_routing",
        "critic_review",
        "critic_result",
        "routing",
        "day_routed",
        "validating",
    ]
    data: dict = Field(default_factory=dict)
    content: str | None = None
