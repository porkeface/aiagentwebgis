"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.poi import router as poi_router

router = APIRouter()

router.include_router(poi_router)
