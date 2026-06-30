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

        Each emitted event is a flat dict with both:
        - a top-level ``type`` discriminator (SSE event name)
        - the event's payload as top-level fields (pois, city, days, content, …)
        - a convenience ``data`` field containing the same payload, for
          consumers that prefer to read via ``event["data"]``.

        Args:
            state: Current AgentState with planning results.

        Returns:
            New state dict with 'structured_plan' set to list of event dicts.
        """
        events: list[dict[str, Any]] = []

        # 1. POI result event — send candidate POIs to map
        candidate_pois = state.get("candidate_pois", [])
        if candidate_pois:
            center = self._calc_center(candidate_pois)
            pois_payload = [
                {
                    "id": poi.get("id", 0),
                    "name": poi.get("name", ""),
                    "category": poi.get("category", ""),
                    "address": poi.get("address"),
                    "lng": poi.get("lng", 0.0),
                    "lat": poi.get("lat", 0.0),
                    "rating": poi.get("rating"),
                    "review_count": poi.get("review_count"),
                    "tags": poi.get("tags", []),
                    "photo": poi.get("photo"),
                    "description": poi.get("description"),
                }
                for poi in candidate_pois
            ]
            poi_event = {
                "type": "poi_result",
                "pois": pois_payload,
                "center": center,
                "zoom": _DEFAULT_ZOOM,
            }
            poi_event["data"] = {
                "pois": pois_payload,
                "center": center,
                "zoom": _DEFAULT_ZOOM,
            }
            events.append(poi_event)

        # 2. Route result event — send daily plans with embedded route segments
        daily_plans = state.get("daily_plans", [])
        route_polylines = state.get("route_polylines", [])
        if daily_plans:
            # Build a lookup: day_number → list of polyline segments
            segments_by_day: dict[int, list[dict[str, Any]]] = {}
            for pl in route_polylines:
                day_num = pl.get("day", 1)
                segments_by_day.setdefault(day_num, []).append({
                    "from_poi_id": pl.get("from_poi_id"),
                    "to_poi_id": pl.get("to_poi_id"),
                    "distance_km": pl.get("distance_km", 0.0),
                    "duration_min": pl.get("duration_min", 0),
                })

            formatted_daily_plans = []
            for day_plan in daily_plans:
                day_num = day_plan.get("day", 1)
                formatted_day = {
                    "day": day_num,
                    "day_title": day_plan.get("day_title", ""),
                    "pois": day_plan.get("pois", []),
                    "total_distance_km": day_plan.get("total_distance_km", 0.0),
                    "segments": segments_by_day.get(day_num, []),
                }
                formatted_daily_plans.append(formatted_day)

            route_event = {
                "type": "route_result",
                "daily_plans": formatted_daily_plans,
                "polylines": route_polylines,
            }
            route_event["data"] = {
                "daily_plans": formatted_daily_plans,
                "polylines": route_polylines,
            }
            events.append(route_event)

        # 3. Plan summary event
        city = state.get("city")
        days = state.get("days")
        if city and days:
            summary_event = {
                "type": "plan_summary",
                "city": city,
                "days": days,
            }
            summary_event["data"] = {
                "city": city,
                "days": days,
            }
            events.append(summary_event)

        # 4. Text event (always emitted)
        response_text = state.get("response_text", "")
        text_event = {
            "type": "text",
            "content": response_text,
        }
        text_event["data"] = {"content": response_text}
        events.append(text_event)

        # Return new state dict (immutable pattern)
        return {**state, "structured_plan": events}
