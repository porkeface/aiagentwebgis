"""Chat session history API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_session
from app.schemas.chat import ChatSessionDetail, ChatSessionListItem, ChatSessionUpdate
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat-sessions", tags=["ChatSession"])


def _to_list_item(session) -> dict:
    """Convert an ORM ChatSession to a dict matching ChatSessionListItem."""
    messages = session.messages_json or []
    msg_count = len(messages) if isinstance(messages, list) else 0
    return {
        "id": session.id,
        "thread_id": session.thread_id,
        "title": session.title,
        "message_count": msg_count,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _to_detail(session) -> dict:
    """Convert an ORM ChatSession to a dict matching ChatSessionDetail."""
    messages = session.messages_json
    if messages is None:
        messages = []
    return {
        "id": session.id,
        "thread_id": session.thread_id,
        "title": session.title,
        "messages": messages,
        "agent_state_json": session.agent_state_json,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("", summary="List chat sessions")
async def list_chat_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """List chat sessions for the authenticated user."""
    result = await chat_service.list_sessions(
        db=db, user_id=user_id, page=page, size=size,
    )
    items = [_to_list_item(s) for s in result["items"]]
    return {
        "success": True,
        "data": {"total": result["total"], "items": items},
    }


@router.get("/{thread_id}", summary="Get chat session detail")
async def get_chat_session(
    thread_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Get full chat session including messages and agent state."""
    session = await chat_service.get_session(
        db=db, user_id=user_id, thread_id=thread_id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True, "data": _to_detail(session)}


@router.patch("/{thread_id}", summary="Update chat session title")
async def update_chat_session(
    thread_id: str,
    payload: ChatSessionUpdate,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Update the title of a chat session."""
    session = await chat_service.update_title(
        db=db, user_id=user_id, thread_id=thread_id, title=payload.title,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True, "data": _to_list_item(session)}


@router.delete("/{thread_id}", summary="Delete chat session")
async def delete_chat_session(
    thread_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Delete a chat session and its history."""
    deleted = await chat_service.delete_session(
        db=db, user_id=user_id, thread_id=thread_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True, "data": {"deleted": True}}
