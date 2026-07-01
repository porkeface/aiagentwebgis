"""Agent tools package — @tool-decorated functions for LangChain ReAct agent.

Exports:
- AGENT_TOOLS — list of @tool functions for create_react_agent
- get_amap — singleton AmapService factory
"""

from __future__ import annotations

import logging
import os

from app.services.amap_service import AmapService

logger = logging.getLogger(__name__)

from agent.tools.poi_search import search_pois, search_nearby
from agent.tools.geocoding import geocode, reverse_geocode
from agent.tools.route_planning import plan_route
from agent.tools.spatial_analysis import score_pois
from agent.tools.weather import get_weather
from agent.tools.optimize_route import optimize_route
from agent.tools.submit_plan import submit_plan
from agent.tools.geo_partition import geo_partition
from agent.tools.plan_day_route import plan_day_route

# ---------------------------------------------------------------------------
# Singleton AmapService factory
# ---------------------------------------------------------------------------

_amap_instance: AmapService | None = None


def get_amap() -> AmapService:
    """Return a shared AmapService singleton."""
    global _amap_instance  # noqa: PLW0603
    if _amap_instance is None:
        from app.config import settings
        api_key = settings.amap_api_key
        if not api_key:
            logger.warning("AMAP_API_KEY is empty — POI search will fail")
        _amap_instance = AmapService(api_key=api_key)
    return _amap_instance


async def close_amap() -> None:
    """Close the AmapService singleton's HTTP client."""
    global _amap_instance  # noqa: PLW0603
    if _amap_instance is not None:
        await _amap_instance.close()
        _amap_instance = None


# ---------------------------------------------------------------------------
# Agent tool list — passed to create_react_agent
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    search_pois,
    search_nearby,
    plan_route,
    optimize_route,
    score_pois,
    submit_plan,
    geocode,
    reverse_geocode,
    get_weather,
    geo_partition,
    plan_day_route,
]

__all__ = [
    "AGENT_TOOLS",
    "get_amap",
    "close_amap",
    "search_pois",
    "search_nearby",
    "plan_route",
    "optimize_route",
    "score_pois",
    "submit_plan",
    "geocode",
    "reverse_geocode",
    "get_weather",
    "geo_partition",
    "plan_day_route",
]
