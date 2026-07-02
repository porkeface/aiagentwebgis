"""Admin API endpoints — configuration, user management, data management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_admin
from app.database import get_session
from app.models.chat import ChatSession
from app.models.poi import POI
from app.models.trip import Trip, TripDay, TripDayPOI
from app.models.user import User
from app.services import config_service
from app.services.auth_service import hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class ConfigUpdateRequest(BaseModel):
    updates: dict[str, str]


class UserPatchRequest(BaseModel):
    is_admin: bool | None = None
    password: str | None = None


# ── Config endpoints ─────────────────────────────────────────────────────────


@router.get("/config", summary="Get current config")
async def get_admin_config(
    user_id: int = Depends(require_admin),
) -> dict:
    """Return the current .env configuration with secrets masked."""
    return {"success": True, "data": config_service.get_config()}


@router.put("/config", summary="Update config")
async def update_admin_config(
    body: ConfigUpdateRequest,
    user_id: int = Depends(require_admin),
) -> dict:
    """Update .env configuration. Returns which keys need a restart."""
    try:
        result = config_service.update_config(body.updates)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "data": result}


# ── User management ──────────────────────────────────────────────────────────


@router.get("/users", summary="List all users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """List all registered users with their admin status."""
    count_res = await db.execute(select(func.count()).select_from(User))
    total = count_res.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(size)
        if hasattr(User, "created_at")
        else select(User).order_by(User.id.desc()).offset(offset).limit(size)
    )
    users = result.scalars().all()

    return {
        "success": True,
        "data": {
            "total": total,
            "items": [
                {
                    "id": u.id,
                    "username": u.username,
                    "nickname": u.nickname,
                    "email": u.email,
                    "is_admin": u.is_admin,
                }
                for u in users
            ],
        },
    }


@router.patch("/users/{target_id}", summary="Update user")
async def patch_user(
    target_id: int,
    body: UserPatchRequest,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """Toggle admin status or reset password for a user. Cannot modify self."""
    if target_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin account")

    result = await db.execute(select(User).where(User.id == target_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.password:
        user.hashed_password = hash_password(body.password)

    await db.flush()

    return {
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
        },
    }


@router.delete("/users/{target_id}", summary="Delete user")
async def delete_user(
    target_id: int,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """Delete a user and all their associated data. Cannot delete self."""
    if target_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == target_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()
    return {"success": True, "data": {"deleted": user.id}}


# ── Data management ──────────────────────────────────────────────────────────


@router.get("/stats", summary="Get data statistics")
async def get_stats(
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """Return counts of all major entities."""
    users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    trips = (await db.execute(select(func.count()).select_from(Trip))).scalar() or 0
    pois = (await db.execute(select(func.count()).select_from(POI))).scalar() or 0
    sessions = (await db.execute(select(func.count()).select_from(ChatSession))).scalar() or 0

    return {
        "success": True,
        "data": {"users": users, "trips": trips, "pois": pois, "chat_sessions": sessions},
    }


@router.get("/trips", summary="List all trips")
async def list_all_trips(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """List all trips across all users."""
    count_res = await db.execute(select(func.count()).select_from(Trip))
    total = count_res.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        select(Trip).order_by(Trip.created_at.desc()).offset(offset).limit(size)
    )
    trips = result.scalars().all()

    return {
        "success": True,
        "data": {
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "city": t.city,
                    "days": (t.end_date - t.start_date).days + 1,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                }
                for t in trips
            ],
        },
    }


@router.delete("/trips/{trip_id}", summary="Delete any trip")
async def delete_any_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """Delete a trip by ID (admin override, no ownership check)."""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    await db.delete(trip)
    await db.flush()
    return {"success": True, "data": {"deleted": trip.id}}


@router.get("/sessions", summary="List all chat sessions")
async def list_all_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """List all chat sessions across all users."""
    count_res = await db.execute(select(func.count()).select_from(ChatSession))
    total = count_res.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.updated_at.desc()).offset(offset).limit(size)
    )
    sessions = result.scalars().all()

    return {
        "success": True,
        "data": {
            "total": total,
            "items": [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "thread_id": s.thread_id,
                    "title": s.title,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ],
        },
    }


@router.delete("/sessions/{session_id}", summary="Delete any chat session")
async def delete_any_session(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(require_admin),
) -> dict:
    """Delete a chat session by ID (admin override)."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    await db.delete(session)
    await db.flush()
    return {"success": True, "data": {"deleted": session.id}}


# ── Admin check (used by frontend guard) ────────────────────────────────────


@router.get("/check", summary="Check if current user is admin")
async def check_admin(
    user_id: int = Depends(require_admin),
) -> dict:
    """Return success if the current user is an admin. Used by frontend guard."""
    return {"success": True, "data": {"is_admin": True}}
