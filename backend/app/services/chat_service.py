"""Chat session persistence service.

Handles saving/loading conversation history alongside map snapshots
so the frontend can restore a past session in full (messages + POIs + routes).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 80


def _extract_title(messages: list[dict]) -> str:
    """Derive a short title from the first user message."""
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "user":
            content = str(m.get("content", "")).strip()
            if content:
                return content[:MAX_TITLE_LENGTH] + ("…" if len(content) > MAX_TITLE_LENGTH else "")
    return "新对话"


async def save_or_update_session(
    db: AsyncSession,
    user_id: int,
    thread_id: str,
    messages: list[dict],
    agent_state: dict | None = None,
) -> ChatSession:
    """Upsert a chat session for the given user + thread_id.

    On first call (INSERT): auto-generates a title from the first user message.
    On subsequent calls (UPDATE): keeps the existing title, updates messages + state.
    """
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.thread_id == thread_id,
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        title = _extract_title(messages)
        session = ChatSession(
            user_id=user_id,
            thread_id=thread_id,
            title=title,
            messages_json=messages,
            agent_state_json=agent_state,
        )
        db.add(session)
    else:
        session.messages_json = messages
        session.agent_state_json = agent_state

    await db.flush()
    return session


async def list_sessions(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """List chat sessions for a user, newest first."""
    count_result = await db.execute(
        select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .offset(offset)
        .limit(size)
    )
    return {"total": total, "items": list(result.scalars().all())}


async def get_session(
    db: AsyncSession,
    user_id: int,
    thread_id: str,
) -> ChatSession | None:
    """Get a single chat session by thread_id, with ownership check."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.thread_id == thread_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_session(
    db: AsyncSession,
    user_id: int,
    thread_id: str,
) -> bool:
    """Delete a chat session. Returns False if not found."""
    session = await get_session(db, user_id, thread_id)
    if session is None:
        return False
    await db.delete(session)
    await db.flush()
    return True


async def update_title(
    db: AsyncSession,
    user_id: int,
    thread_id: str,
    title: str,
) -> ChatSession | None:
    """Update just the title of a chat session."""
    session = await get_session(db, user_id, thread_id)
    if session is None:
        return None
    session.title = title
    await db.flush()
    return session
