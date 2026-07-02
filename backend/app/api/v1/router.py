"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.agent import router as agent_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat_sessions import router as chat_sessions_router
from app.api.v1.poi import router as poi_router
from app.api.v1.trip import router as trip_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(poi_router)
router.include_router(agent_router)
router.include_router(trip_router)
router.include_router(chat_sessions_router)
router.include_router(admin_router)
