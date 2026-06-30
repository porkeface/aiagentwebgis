"""Trip service layer with CRUD operations and user ownership checks."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.poi import POI
from app.models.trip import Trip, TripDay, TripDayPOI
from app.schemas.trip import SavePlanRequest, TripCreate

logger = logging.getLogger(__name__)


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
        title=trip_data.title or f"{trip_data.city} {trip_data.days}日游",
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


async def save_plan(
    db: AsyncSession,
    user_id: int,
    plan: SavePlanRequest,
) -> Trip:
    """Persist an AI planner output as a full Trip + TripDay + TripDayPOI rows.

    This is the single-call endpoint used by the frontend "Save Trip" button:
    the planner has produced a ``daily_plans`` list and the user wants to keep
    it.  Unlike ``create_trip`` this also writes the per-day POI assignments
    (TripDayPOI) so the plan can be reloaded later with full stop detail.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user.
        plan: Full AI plan to persist (city, days, daily_plans with POIs).

    Returns:
        The created Trip with days/pois eagerly loaded.

    Raises:
        ValueError: If the plan has no days / no POIs.
    """
    if not plan.daily_plans:
        raise ValueError("Plan has no daily plans to save")

    # Validate daily_plans shape: number of plans must match plan.days and
    # each day number must be in [1, plan.days]. Prevents malformed clients
    # from creating trips with the wrong number of day buckets.
    if len(plan.daily_plans) != plan.days:
        raise ValueError(
            f"daily_plans length ({len(plan.daily_plans)}) does not match "
            f"plan.days ({plan.days})"
        )
    expected_days = set(range(1, plan.days + 1))
    actual_days = {day.day for day in plan.daily_plans}
    if actual_days != expected_days:
        raise ValueError(
            f"daily_plans day numbers must be a contiguous 1..{plan.days} set, "
            f"got {sorted(actual_days)}"
        )

    # Collect all referenced POI ids so we can resolve them in a single query.
    requested_poi_ids: set[int] = set()
    amap_pois_to_create: list[dict[str, Any]] = []  # POIs from Amap not yet in DB

    for day_plan in plan.daily_plans:
        for poi in day_plan.pois:
            if isinstance(poi.id, int):
                requested_poi_ids.add(poi.id)
            elif isinstance(poi.id, str) and poi.id:
                # String ID = Amap POI, need to create in DB
                amap_pois_to_create.append({
                    "amap_id": poi.id,
                    "name": poi.name,
                    "category": poi.category,
                    "lng": poi.lng,
                    "lat": poi.lat,
                    "rating": poi.rating,
                    "address": poi.address,
                    "tags": poi.tags,
                    "photo": poi.photo,
                })

    poi_lookup: dict[int, POI] = {}
    if requested_poi_ids:
        stmt = select(POI).where(POI.id.in_(requested_poi_ids))
        result = await db.execute(stmt)
        for poi in result.scalars().all():
            poi_lookup[poi.id] = poi

    # --- Amap POI resolution: batch the existing check, then create any
    #     missing ones. Catching IntegrityError on flush (race against the
    #     unique partial index on extra_data->>'amap_id') re-queries and
    #     reuses the winner. ---
    amap_poi_id_map: dict[str, int] = {}  # amap_id → DB id
    if amap_pois_to_create:
        amap_ids = {p["amap_id"] for p in amap_pois_to_create}
        existing_stmt = select(POI).where(
            POI.extra_data["amap_id"].astext.in_(amap_ids)
        )
        existing_result = await db.execute(existing_stmt)
        for existing in existing_result.scalars().all():
            amap_id_value = (
                existing.extra_data.get("amap_id")
                if isinstance(existing.extra_data, dict)
                else None
            )
            if amap_id_value:
                amap_poi_id_map[amap_id_value] = existing.id
                poi_lookup[existing.id] = existing

        for poi_data in amap_pois_to_create:
            amap_id = poi_data["amap_id"]
            if amap_id in amap_poi_id_map:
                continue
            poi = POI(
                name=poi_data["name"],
                category=poi_data["category"] or "景点",
                city=plan.city,
                location=from_shape(Point(poi_data["lng"], poi_data["lat"]), srid=4326),
                rating=poi_data.get("rating"),
                tags=poi_data.get("tags") or [],
                description=poi_data.get("description"),
                extra_data={
                    "amap_id": amap_id,
                    "photo": poi_data.get("photo"),
                    "address": poi_data.get("address"),
                },
            )
            db.add(poi)
            try:
                await db.flush()
            except IntegrityError:
                # Another concurrent request inserted the same amap_id first.
                # Roll back our half-inserted row and reuse the winner.
                await db.rollback()
                winner_stmt = select(POI).where(
                    POI.extra_data["amap_id"].astext == amap_id
                )
                winner = (await db.execute(winner_stmt)).scalar_one_or_none()
                if winner is None:
                    raise
                amap_poi_id_map[amap_id] = winner.id
                poi_lookup[winner.id] = winner
                continue
            amap_poi_id_map[amap_id] = poi.id
            poi_lookup[poi.id] = poi

    # Compute date range from today.
    start_date = date.today()
    end_date = start_date + timedelta(days=plan.days - 1)

    trip = Trip(
        user_id=user_id,
        title=plan.title or f"{plan.city} {plan.days}日游",
        city=plan.city,
        start_date=start_date,
        end_date=end_date,
        status="planned",
        notes=None,
    )
    db.add(trip)
    await db.flush()

    # Write each day's stops.  Missing POIs are skipped (log a warning).
    for day_plan in plan.daily_plans:
        day = TripDay(
            trip_id=trip.id,
            day_number=day_plan.day,
            date=start_date + timedelta(days=day_plan.day - 1),
            notes=day_plan.day_title,
        )
        db.add(day)
        await db.flush()

        for sort_order, poi_in in enumerate(day_plan.pois, start=1):
            # Resolve POI id: could be int (DB) or str (Amap)
            resolved_id: int | None = None
            if isinstance(poi_in.id, int):
                resolved_id = poi_in.id
            elif isinstance(poi_in.id, str):
                resolved_id = amap_poi_id_map.get(poi_in.id)

            if resolved_id is None or resolved_id not in poi_lookup:
                logger.warning(
                    "save_plan: POI id=%s not found in DB — skipping", poi_in.id,
                )
                continue
            db.add(TripDayPOI(
                trip_day_id=day.id,
                poi_id=resolved_id,
                sort_order=sort_order,
                score=poi_in.rating,
                notes=None,
            ))

    await db.flush()

    # Eagerly load the full hierarchy for the response.
    stmt = (
        select(Trip)
        .where(Trip.id == trip.id)
        .options(
            selectinload(Trip.days).selectinload(TripDay.pois).selectinload(TripDayPOI.poi),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


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
            selectinload(Trip.days).selectinload(TripDay.pois).selectinload(TripDayPOI.poi),
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
