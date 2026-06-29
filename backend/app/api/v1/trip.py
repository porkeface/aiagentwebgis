"""Trip CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.trip import TripCreate, TripDetailResponse, TripResponse
from app.services import trip_service

router = APIRouter(prefix="/api/v1/trips", tags=["Trip"])


# --- Placeholder auth dependency (will be replaced by JWT in T4.5) ---

async def get_current_user() -> int:
    """Placeholder auth dependency.

    Returns a mock user_id. Real JWT auth will be implemented in T4.5.
    """
    return 1


# --- Update schema ---

class TripUpdate(BaseModel):
    """Request schema for updating a trip."""

    title: str | None = None
    status: str | None = None
    notes: str | None = None


# --- Endpoints ---

@router.post("")
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


@router.get("")
async def list_trips_endpoint(
    page: int = 1,
    size: int = 20,
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


@router.get("/{trip_id}")
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
        pois = [
            {
                "poi_id": p.poi_id,
                "sort_order": p.sort_order,
                "arrival_time": p.arrival_time,
                "departure_time": p.departure_time,
                "score": p.score,
                "notes": p.notes,
                "name": None,
                "category": None,
                "lng": None,
                "lat": None,
            }
            for p in day.pois
        ]
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


@router.put("/{trip_id}")
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


@router.delete("/{trip_id}")
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
