"""Formatter Node — SSE event packaging from AgentState.

Reads the final AgentState after planning and produces a list of
SSE (Server-Sent Events) event dicts that the API layer can stream
to the frontend.

Event types:
- poi_result:    POI list with calculated center and zoom
- route_result:  Daily plans with route polylines
- plan_summary:  Trip city/days summary
- text:          Response text for the user
"""

from __future__ import annotations

from typing import Any

from agent.state import AgentState


# Default map center (Beijing) used when no POIs are available
_DEFAULT_CENTER: dict[str, float] = {"lng": 116.4, "lat": 39.9}
_DEFAULT_ZOOM: int = 12


class FormatterNode:
    """Formats AgentState into a list of SSE event dicts.

    Each event is a plain dict with at least a 'type' key.
    Events are stored in state['structured_plan'] for downstream
    consumption by the SSE streaming endpoint.
    """

    def _calc_center(self, pois: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate the average lng/lat center of a list of POIs.

        Args:
            pois: List of POI dicts, each containing 'lng' and 'lat' keys.

        Returns:
            Dict with 'lng' and 'lat' keys representing the center point.
            Returns default center (Beijing) if the list is empty.
        """
        if not pois:
            return dict(_DEFAULT_CENTER)

        total_lng = sum(poi.get("lng", 0.0) for poi in pois)
        total_lat = sum(poi.get("lat", 0.0) for poi in pois)
        count = len(pois)

        return {
            "lng": total_lng / count,
            "lat": total_lat / count,
        }

    async def format(self, state: AgentState) -> dict[str, Any]:
        """Format AgentState into a list of SSE events.

        Reads state fields and emits events conditionally:
        - candidate_pois non-empty → poi_result
        - daily_plans non-empty → route_result
        - city and days present → plan_summary
        - always → text

        Args:
            state: Current AgentState with planning results.

        Returns:
            New state dict with 'structured_plan' set to list of event dicts.
        """
        events: list[dict[str, Any]] = []

        # 1. POI result event
        candidate_pois = state.get("candidate_pois", [])
        if candidate_pois:
            center = self._calc_center(candidate_pois)
            events.append({
                "type": "poi_result",
                "pois": candidate_pois,
                "center": center,
                "zoom": _DEFAULT_ZOOM,
            })

        # 2. Route result event
        daily_plans = state.get("daily_plans", [])
        if daily_plans:
            events.append({
                "type": "route_result",
                "daily_plans": daily_plans,
                "polylines": state.get("route_polylines", []),
            })

        # 3. Plan summary event
        city = state.get("city")
        days = state.get("days")
        if city and days:
            events.append({
                "type": "plan_summary",
                "city": city,
                "days": days,
            })

        # 4. Text event (always emitted)
        response_text = state.get("response_text", "")
        events.append({
            "type": "text",
            "content": response_text,
        })

        # Return new state dict (immutable pattern)
        return {**state, "structured_plan": events}
