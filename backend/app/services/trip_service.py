"""Trip service layer with CRUD operations and user ownership checks."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trip import Trip, TripDay, TripDayPOI
from app.schemas.trip import TripCreate


async def create_trip(
    db: AsyncSession,
    user_id: int,
    trip_data: TripCreate,
) -> Trip:
    """Create a new trip for the given user.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user.
        trip_data: Trip creation data from request body.

    Returns:
        The newly created Trip ORM instance.
    """
    start_date = date.today()
    end_date = start_date + timedelta(days=trip_data.days - 1)

    trip = Trip(
        user_id=user_id,
        title=f"{trip_data.city} {trip_data.days}日游",
        city=trip_data.city,
        start_date=start_date,
        end_date=end_date,
        status="draft",
        notes=None,
    )
    db.add(trip)
    await db.flush()

    # Create TripDay entries for each day
    for day_num in range(1, trip_data.days + 1):
        day = TripDay(
            trip_id=trip.id,
            day_number=day_num,
            date=start_date + timedelta(days=day_num - 1),
        )
        db.add(day)
    await db.flush()

    # Eagerly load days relationship for response
    stmt = (
        select(Trip)
        .where(Trip.id == trip.id)
        .options(selectinload(Trip.days))
    )
    result = await db.execute(stmt)
    trip = result.scalar_one()

    return trip


async def get_trip(
    db: AsyncSession,
    trip_id: int,
    user_id: int,
) -> Trip | None:
    """Get a single trip with ownership check.

    Args:
        db: Async database session.
        trip_id: ID of the trip.
        user_id: ID of the authenticated user.

    Returns:
        Trip if found and owned by user, None otherwise.
    """
    stmt = (
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.pois),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_trips(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """List trips for a user with pagination.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user.
        page: Page number (1-indexed, default 1).
        size: Page size (default 20).

    Returns:
        {"total": int, "items": list[Trip]}
    """
    # Count total
    count_stmt = (
        select(func.count())
        .select_from(Trip)
        .where(Trip.user_id == user_id)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginated query
    offset = (page - 1) * size
    stmt = (
        select(Trip)
        .where(Trip.user_id == user_id)
        .order_by(Trip.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    trips = list(result.scalars().all())

    return {"total": total, "items": trips}


async def update_trip(
    db: AsyncSession,
    trip_id: int,
    user_id: int,
    updates: dict[str, Any],
) -> Trip | None:
    """Update a trip with ownership check.

    Only allows updating specific safe fields: title, status, notes.

    Args:
        db: Async database session.
        trip_id: ID of the trip.
        user_id: ID of the authenticated user.
        updates: Dictionary of field updates.

    Returns:
        Updated Trip if found and owned by user, None otherwise.
    """
    stmt = (
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()

    if trip is None:
        return None

    # Only allow safe fields to be updated
    allowed_fields = {"title", "status", "notes"}
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(trip, key, value)

    await db.flush()
    return trip


async def delete_trip(
    db: AsyncSession,
    trip_id: int,
    user_id: int,
) -> bool:
    """Delete a trip with ownership check.

    Cascade delete removes associated TripDay and TripDayPOI records.

    Args:
        db: Async database session.
        trip_id: ID of the trip.
        user_id: ID of the authenticated user.

    Returns:
        True if deleted, False if not found or not owned.
    """
    stmt = (
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()

    if trip is None:
        return False

    await db.delete(trip)
    await db.flush()
    return True
