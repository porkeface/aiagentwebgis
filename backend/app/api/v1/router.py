"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.agent import router as agent_router
from app.api.v1.poi import router as poi_router
from app.api.v1.trip import router as trip_router

router = APIRouter()

router.include_router(poi_router)
router.include_router(agent_router)
router.include_router(trip_router)
