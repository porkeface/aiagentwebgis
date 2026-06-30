"""Trip CRUD API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_session
from app.schemas.trip import (
    SavePlanRequest,
    TripCreate,
    TripDetailResponse,
    TripResponse,
)
from app.services import trip_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trips", tags=["Trip"])


# --- Update schema ---

class TripUpdate(BaseModel):
    """Request schema for updating a trip."""

    title: str | None = None
    status: str | None = None
    notes: str | None = None


# --- Endpoints ---

@router.post(
    "",
    summary="Create a new trip",
    description="Create a trip with city, duration, preferences. Returns auto-generated title and date range.",
)
async def create_trip_endpoint(
    trip_data: TripCreate,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Create a new trip.

    Returns the created trip with auto-generated title and date range.
    """
    trip = await trip_service.create_trip(
        db=db,
        user_id=user_id,
        trip_data=trip_data,
    )
    return {
        "success": True,
        "data": {
            "id": trip.id,
            "city": trip.city,
            "days": (trip.end_date - trip.start_date).days + 1,
            "status": trip.status,
            "created_at": trip.created_at.isoformat(),
        },
    }


@router.post(
    "/save-plan",
    summary="Persist an AI planner output as a Trip",
    description=(
        "Takes the AI planner's daily_plans (city, days, stops per day) and "
        "materialises them as a Trip with TripDay + TripDayPOI rows. The user "
        "can later reload the plan via GET /trips/:id."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def save_plan_endpoint(
    plan: SavePlanRequest,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Persist a full AI plan as a Trip.

    Returns the created trip's summary (id, city, days, status, created_at).
    Missing POI ids are logged and skipped rather than failing the whole request.
    """
    try:
        trip = await trip_service.save_plan(db=db, user_id=user_id, plan=plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("save_plan failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to save trip plan",
        ) from exc

    return {
        "success": True,
        "data": {
            "id": trip.id,
            "city": trip.city,
            "days": (trip.end_date - trip.start_date).days + 1,
            "status": trip.status,
            "created_at": trip.created_at.isoformat(),
        },
    }


@router.get(
    "",
    summary="List user trips",
    description="List trips for the authenticated user with pagination, ordered by creation date.",
)
async def list_trips_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """List trips with pagination.

    Returns paginated trip summaries ordered by creation date.
    """
    result = await trip_service.list_trips(
        db=db,
        user_id=user_id,
        page=page,
        size=size,
    )
    items = [
        {
            "id": t.id,
            "title": t.title,
            "city": t.city,
            "days": (t.end_date - t.start_date).days + 1,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in result["items"]
    ]
    return {
        "success": True,
        "data": {
            "total": result["total"],
            "items": items,
        },
    }


@router.get(
    "/{trip_id}",
    summary="Get trip detail",
    description="Get full trip detail with daily plans and POIs. Returns 404 if trip not found or not owned by user.",
)
async def get_trip_endpoint(
    trip_id: int,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Get trip detail with daily plans and POIs.

    Returns 404 if trip not found or not owned by user.
    """
    trip = await trip_service.get_trip(
        db=db,
        trip_id=trip_id,
        user_id=user_id,
    )
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    daily_plans = []
    for day in trip.days:
        pois = []
        for p in day.pois:
            poi_obj = p.poi
            if poi_obj and poi_obj.location:
                try:
                    point = to_shape(poi_obj.location)
                    lng = point.x
                    lat = point.y
                except Exception:
                    logger.warning("Failed to parse geometry for POI id=%s", poi_obj.id)
                    lng = None
                    lat = None
            else:
                lng = None
                lat = None
            pois.append({
                "poi_id": p.poi_id,
                "sort_order": p.sort_order,
                "arrival_time": p.arrival_time,
                "departure_time": p.departure_time,
                "score": p.score,
                "notes": p.notes,
                "name": poi_obj.name if poi_obj else None,
                "category": poi_obj.category if poi_obj else None,
                "lng": lng,
                "lat": lat,
                "rating": poi_obj.rating if poi_obj else None,
                "address": (poi_obj.extra_data or {}).get("address") if poi_obj else None,
                "tags": (poi_obj.tags or []) if poi_obj else [],
            })
        daily_plans.append({
            "day_number": day.day_number,
            "date": day.date.isoformat(),
            "notes": day.notes,
            "pois": pois,
        })

    return {
        "success": True,
        "data": {
            "id": trip.id,
            "city": trip.city,
            "days": (trip.end_date - trip.start_date).days + 1,
            "status": trip.status,
            "created_at": trip.created_at.isoformat(),
            "daily_plans": daily_plans,
        },
    }


@router.put(
    "/{trip_id}",
    summary="Update a trip",
    description="Update trip title, status, or notes. Returns 404 if not found or not owned by user.",
)
async def update_trip_endpoint(
    trip_id: int,
    updates: TripUpdate,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Update a trip.

    Only title, status, and notes can be updated.
    Returns 404 if trip not found or not owned by user.
    """
    update_dict = updates.model_dump(exclude_unset=True)
    trip = await trip_service.update_trip(
        db=db,
        trip_id=trip_id,
        user_id=user_id,
        updates=update_dict,
    )
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    return {
        "success": True,
        "data": {
            "id": trip.id,
            "city": trip.city,
            "days": (trip.end_date - trip.start_date).days + 1,
            "status": trip.status,
            "title": trip.title,
            "created_at": trip.created_at.isoformat(),
        },
    }


@router.delete(
    "/{trip_id}",
    summary="Delete a trip",
    description="Delete a trip and cascade all associated TripDay and TripDayPOI records. Returns 404 if not found.",
)
async def delete_trip_endpoint(
    trip_id: int,
    db: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> dict:
    """Delete a trip.

    Cascade deletes all associated TripDay and TripDayPOI records.
    Returns 404 if trip not found or not owned by user.
    """
    deleted = await trip_service.delete_trip(
        db=db,
        trip_id=trip_id,
        user_id=user_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found")

    return {
        "success": True,
        "data": {"deleted": True},
    }
