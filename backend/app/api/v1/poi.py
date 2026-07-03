"""POI search API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.poi import POIResponse
from app.services.poi_service import search_pois

router = APIRouter(prefix="/api/v1/poi", tags=["POI"])


@router.get("/search", response_model=dict)
async def search_pois_endpoint(
    city: str = Query(..., description="City name"),
    category: str | None = Query(None, description="Category filter"),
    keyword: str | None = Query(None, description="Keyword search in name/description"),
    bbox: str | None = Query(
        None,
        description="Bounding box: min_lng,min_lat,max_lng,max_lat",
    ),
    rating_min: float | None = Query(None, ge=0.0, le=5.0, description="Minimum rating"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Search POIs with filters and pagination.

    Returns paginated results with total count.
    """
    # Parse bbox string to list of floats.  Reject malformed input with 400
    # instead of silently dropping the spatial filter — the previous behaviour
    # returned the full unfiltered result set and gave the client no signal
    # that their query was bad.
    bbox_list: list[float] | None = None
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
        except (ValueError, AttributeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "bbox must be four comma-separated floats: "
                    "min_lng,min_lat,max_lng,max_lat"
                ),
            ) from exc
        if len(parts) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bbox must contain exactly 4 values: min_lng,min_lat,max_lng,max_lat",
            )
        bbox_list = parts

    result = await search_pois(
        db=db,
        city=city,
        category=category,
        keyword=keyword,
        bbox=bbox_list,
        rating_min=rating_min,
        page=page,
        size=size,
    )

    # Convert POIResponse objects to dicts
    items = [item.model_dump() for item in result["items"]]

    return {
        "success": True,
        "data": {
            "total": result["total"],
            "items": items,
        },
    }
