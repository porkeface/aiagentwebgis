"""Agent tools package — wraps AmapService for LangGraph tool registration.

Provides async tool functions that the agent graph can invoke:
- search_pois_tool / search_nearby_tool (poi_search.py)
- geocode_tool / reverse_geocode_tool (geocoding.py)
- plan_route_tool (route_planning.py)
- score_pois_tool (spatial_analysis.py)
- get_weather_tool (weather.py)

Also exports:
- get_amap() — singleton factory for AmapService
- ALL_TOOLS — list of all tool functions for LangGraph registration
"""

from __future__ import annotations

import logging
import os

from app.services.amap_service import AmapService

logger = logging.getLogger(__name__)

from agent.tools.poi_search import search_pois_tool, search_nearby_tool
from agent.tools.geocoding import geocode_tool, reverse_geocode_tool
from agent.tools.route_planning import plan_route_tool
from agent.tools.spatial_analysis import score_pois_tool
from agent.tools.weather import get_weather_tool

# ---------------------------------------------------------------------------
# Singleton AmapService factory
# ---------------------------------------------------------------------------

_amap_instance: AmapService | None = None


def get_amap() -> AmapService:
    """Return a shared AmapService singleton.

    Reads AMAP_API_KEY from app settings (which loads from .env).
    Creates the instance lazily on first call; subsequent calls return
    the same object.
    """
    global _amap_instance  # noqa: PLW0603
    if _amap_instance is None:
        from app.config import settings
        api_key = settings.amap_api_key
        if not api_key:
            logger.warning("AMAP_API_KEY is empty — POI search will fail")
        _amap_instance = AmapService(api_key=api_key)
    return _amap_instance


async def close_amap() -> None:
    """Close the AmapService singleton's HTTP client.

    Should be called from FastAPI's shutdown hook so the underlying
    httpx connection pool is released cleanly when the process exits.
    """
    global _amap_instance  # noqa: PLW0603
    if _amap_instance is not None:
        await _amap_instance.close()
        _amap_instance = None


def _reset_amap_instance() -> None:
    """Reset the singleton — for testing only."""
    global _amap_instance  # noqa: PLW0603
    _amap_instance = None


# ---------------------------------------------------------------------------
# ALL_TOOLS — for LangGraph tool registration
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    search_pois_tool,
    search_nearby_tool,
    geocode_tool,
    reverse_geocode_tool,
    plan_route_tool,
    score_pois_tool,
    get_weather_tool,
]

__all__ = [
    "get_amap",
    "ALL_TOOLS",
    "search_pois_tool",
    "search_nearby_tool",
    "geocode_tool",
    "reverse_geocode_tool",
    "plan_route_tool",
    "score_pois_tool",
    "get_weather_tool",
]
