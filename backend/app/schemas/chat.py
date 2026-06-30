"""Chat session schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionUpdate(BaseModel):
    """Request schema for updating a chat session title."""

    title: str = Field(min_length=1, max_length=255)


class ChatSessionListItem(BaseModel):
    """Lightweight chat session for list views."""

    id: int
    thread_id: str
    title: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetail(BaseModel):
    """Full chat session with messages and map snapshot."""

    id: int
    thread_id: str
    title: str | None = None
    messages: list[dict] = Field(default_factory=list)
    agent_state_json: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
