"""Amap (Gaode Map) API service for POI search, geocoding, and route planning.

Base URL: https://restapi.amap.com/v3 (legacy) / v5 (direction)
Docs: https://lbs.amap.com/api/webservice/summary
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

AMAP_BASE_URL = "https://restapi.amap.com/v3"
AMAP_V5_BASE_URL = "https://restapi.amap.com/v5"

VALID_ROUTE_MODES = frozenset({"walking", "driving", "bicycling", "transit"})

# Retry configuration for Amap API
AMAP_MAX_RETRIES = 3
AMAP_RETRY_BACKOFF_BASE = 0.5  # seconds


def _first_photo(poi: dict[str, Any]) -> str | None:
    """Extract the first photo URL from a POI dict, or None."""
    photos = poi.get("photos")
    if isinstance(photos, list) and photos:
        first = photos[0]
        if isinstance(first, dict):
            url = first.get("url")
            if isinstance(url, str):
                return url
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_rating(poi: dict[str, Any]) -> float | None:
    """Extract rating from biz_ext or deep_info."""
    biz_ext = poi.get("biz_ext")
    if isinstance(biz_ext, dict):
        rating = biz_ext.get("rating")
        if rating is not None:
            try:
                return float(rating)
            except (TypeError, ValueError):
                pass
    return None


def _extract_review_count(poi: dict[str, Any]) -> int | None:
    """Extract review count from deep_info."""
    deep_info = poi.get("deep_info")
    if isinstance(deep_info, dict):
        count = deep_info.get("review_count")
        if count is not None:
            try:
                return int(count)
            except (TypeError, ValueError):
                pass
    return None


def _extract_description(poi: dict[str, Any]) -> str | None:
    """Extract intro/description from deep_info."""
    deep_info = poi.get("deep_info")
    if isinstance(deep_info, dict):
        intro = deep_info.get("intro")
        if isinstance(intro, str) and intro.strip():
            return intro.strip()
    return None


class AmapService:
    """Async client for the Amap (Gaode) REST API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AmapService":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        await self.close()
        return False

    def _get_client(self) -> httpx.AsyncClient:
        """Lazily create and return the shared httpx.AsyncClient.

        A bounded connection pool is used to prevent bursting past Amap's QPS
        limit when many parallel planner requests fire route searches.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=AMAP_BASE_URL,
                timeout=10.0,
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a GET request to the Amap API with automatic key injection and retry.

        Args:
            endpoint: API path relative to base URL (e.g. "place/text").
            params: Optional query parameters.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            ValueError: If the API returns a non-success status.
            httpx.HTTPStatusError: If the HTTP status code is not 2xx.
        """
        client = self._get_client()
        all_params: dict[str, Any] = {"key": self._api_key}
        if params:
            all_params.update(params)

        last_error: Exception | None = None

        for attempt in range(AMAP_MAX_RETRIES):
            try:
                response = await client.get(endpoint, params=all_params)
                response.raise_for_status()

                data: dict[str, Any] = response.json()
                if data.get("status") != "1":
                    info = data.get("info", "Unknown error")
                    infocode = data.get("infocode", "")
                    # QPS rate limit — retry with exponential backoff
                    if infocode == "10021":
                        if attempt < AMAP_MAX_RETRIES - 1:
                            wait_time = AMAP_RETRY_BACKOFF_BASE * (3 ** attempt)
                            logger.warning(
                                "Amap QPS limit hit, retrying in %.1fs (attempt %d/%d)",
                                wait_time, attempt + 1, AMAP_MAX_RETRIES,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                    raise ValueError(
                        f"Amap API error: {info} (code={infocode})"
                    )
                return data

            except (httpx.TimeoutException, httpx.ConnectError, ConnectionError) as e:
                last_error = e
                logger.warning(
                    f"Amap API request failed (attempt {attempt + 1}/{AMAP_MAX_RETRIES}): {e}"
                )
                if attempt < AMAP_MAX_RETRIES - 1:
                    wait_time = AMAP_RETRY_BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted
        if last_error is not None:
            raise last_error
        raise RuntimeError("Amap API request failed after all retries")

    async def search_pois(
        self,
        city: str,
        keyword: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search POIs via the place/text endpoint.

        Args:
            city: City name (required), e.g. "北京".
            keyword: Search keyword, e.g. "故宫".
            category: POI type category, e.g. "景点".
            limit: Max results to return (default 20).

        Returns:
            List of POI dicts with keys: amap_id, name, address, lng, lat, type, city.
        """
        params: dict[str, str] = {
            "city": city,
            "offset": str(limit),
            "extensions": "all",
        }
        if keyword:
            params["keywords"] = keyword
        if category:
            params["types"] = category

        data = await self._request("place/text", params)

        results: list[dict[str, Any]] = []
        for poi in data.get("pois", []):
            location_str = poi.get("location", "")
            lng, lat = 0.0, 0.0
            if location_str and "," in location_str:
                parts = location_str.split(",")
                try:
                    lng = float(parts[0])
                    lat = float(parts[1])
                except (ValueError, IndexError):
                    pass

            city_name = ""
            city_data = poi.get("city")
            if isinstance(city_data, list) and city_data:
                city_name = city_data[0].get("cityname", "")
            elif isinstance(city_data, str):
                city_name = city_data

            results.append(
                {
                    "id": poi.get("id", ""),
                    "amap_id": poi.get("id", ""),
                    "name": poi.get("name", ""),
                    "address": poi.get("address", ""),
                    "lng": lng,
                    "lat": lat,
                    "category": poi.get("type", ""),
                    "city": city_name,
                    "photo": _first_photo(poi),
                    "rating": _extract_rating(poi),
                    "review_count": _extract_review_count(poi),
                    "description": _extract_description(poi),
                }
            )

        return results

    async def search_nearby(
        self,
        lng: float,
        lat: float,
        category: str,
        radius: int = 1000,
    ) -> list[dict[str, Any]]:
        """Search nearby POIs around a coordinate via the place/around endpoint.

        Args:
            lng: Longitude of the center point.
            lat: Latitude of the center point.
            category: POI type category, e.g. "景点".
            radius: Search radius in meters (default 1000).

        Returns:
            List of POI dicts with keys: amap_id, name, address, lng, lat, type.
        """
        params: dict[str, str] = {
            "location": f"{lng},{lat}",
            "types": category,
            "radius": str(radius),
            "offset": "20",
            "extensions": "all",
        }

        data = await self._request("place/around", params)

        results: list[dict[str, Any]] = []
        for poi in data.get("pois", []):
            location_str = poi.get("location", "")
            poi_lng, poi_lat = 0.0, 0.0
            if location_str and "," in location_str:
                parts = location_str.split(",")
                try:
                    poi_lng = float(parts[0])
                    poi_lat = float(parts[1])
                except (ValueError, IndexError):
                    pass

            results.append(
                {
                    "id": poi.get("id", ""),
                    "name": poi.get("name", ""),
                    "address": poi.get("address", ""),
                    "lng": poi_lng,
                    "lat": poi_lat,
                    "category": poi.get("type", ""),
                    "photo": _first_photo(poi),
                    "rating": _extract_rating(poi),
                    "review_count": _extract_review_count(poi),
                    "description": _extract_description(poi),
                }
            )

        return results

    async def geocode(self, address: str) -> tuple[float, float]:
        """Geocode an address to (longitude, latitude).

        Args:
            address: Full address string, e.g. "北京市东城区景山前街4号".

        Returns:
            Tuple of (longitude, latitude).

        Raises:
            ValueError: If no geocode result is found.
        """
        params = {"address": address}
        data = await self._request("geocode/geo", params)

        geocodes = data.get("geocodes", [])
        if not geocodes:
            raise ValueError(f"No geocode result for address: {address}")

        try:
            loc = geocodes[0]["location"].split(",")
            lng = float(loc[0])
            lat = float(loc[1])
            return (lng, lat)
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(
                f"Failed to parse geocode result for '{address}': {e}"
            ) from e

    async def reverse_geocode(
        self, lng: float, lat: float
    ) -> dict[str, str]:
        """Reverse geocode coordinates to an address.

        Args:
            lng: Longitude.
            lat: Latitude.

        Returns:
            Dict with keys: address, city.
        """
        params = {"location": f"{lng},{lat}"}
        data = await self._request("geocode/regeo", params)

        regeocode = data.get("regeocode", {})
        formatted_address = regeocode.get("formatted_address", "")
        address_component = regeocode.get("addressComponent", {})

        city = address_component.get("city", "")
        # Amap returns empty list for direct-administered municipalities
        if isinstance(city, list):
            city = address_component.get("province", "")

        return {
            "address": formatted_address,
            "city": city,
        }

    async def plan_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str = "walking",
    ) -> dict[str, Any]:
        """Plan a route between two points.

        Args:
            origin: (longitude, latitude) of start point.
            destination: (longitude, latitude) of end point.
            mode: Travel mode - "walking", "driving", "bicycling", or "transit".

        Returns:
            Dict with keys:
            - distance_km: Total distance in kilometers.
            - duration_min: Total duration in minutes.
            - polyline: Semicolon-separated coordinate string.
        """
        if mode not in VALID_ROUTE_MODES:
            raise ValueError(
                f"Invalid mode: {mode}. Must be one of {sorted(VALID_ROUTE_MODES)}"
            )

        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
        }

        data = await self._request(f"direction/{mode}", params)

        route = data.get("route", {})
        paths = route.get("paths", [])
        if not paths:
            return {
                "distance_km": 0.0,
                "duration_min": 0.0,
                "polyline": "",
            }

        path = paths[0]
        distance_m = _safe_float(path.get("distance", 0))
        duration_s = _safe_float(path.get("duration", 0))

        # Concatenate polylines from all steps
        steps = path.get("steps", [])
        polyline_parts = [step.get("polyline", "") for step in steps if step.get("polyline")]
        polyline = ";".join(polyline_parts)

        return {
            "distance_km": distance_m / 1000.0,
            "duration_min": duration_s / 60.0,
            "polyline": polyline,
        }

    async def plan_route_with_waypoints(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        waypoints: list[tuple[float, float]] | None = None,
        mode: str = "driving",
    ) -> dict[str, Any]:
        """Plan a multi-waypoint driving route via Amap v5 direction API.

        Uses the newer /v5/direction/driving endpoint which supports up to
        16 waypoints.  Waypoints are visited in the submitted order.

        Args:
            origin: (lng, lat) of the first stop.
            destination: (lng, lat) of the last stop.
            waypoints: Optional list of (lng, lat) for intermediate stops.
            mode: Only "driving" supports waypoints in v5.

        Returns:
            Dict with:
            - distance_km: Total driving distance.
            - duration_min: Total estimated duration.
            - polyline: Concatenated coordinate string for rendering.
            - segments: List of {from, to, distance_km, duration_min} per leg.
        """
        all_coords = [origin]
        if waypoints:
            all_coords.extend(waypoints)
        all_coords.append(destination)

        # Use v3 API with waypoints for compatibility (v5 key may differ)
        params: dict[str, Any] = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
        }

        if mode == "driving" and waypoints:
            # Build waypoints string: lng1,lat1;lng2,lat2
            wp_str = ";".join(f"{w[0]},{w[1]}" for w in waypoints)
            params["waypoints"] = wp_str
            # Strategy: 0=fastest, 2=least distance
            params["strategy"] = "0"
            params["extensions"] = "all"

        data = await self._request(f"direction/{mode}", params)

        route = data.get("route", {})
        paths = route.get("paths", [])
        if not paths:
            return {
                "distance_km": 0.0,
                "duration_min": 0.0,
                "polyline": "",
                "segments": [],
            }

        path = paths[0]
        distance_m = _safe_float(path.get("distance", 0))
        duration_s = _safe_float(path.get("duration", 0))

        # Build per-leg segments from steps
        steps = path.get("steps", [])
        segments: list[dict[str, Any]] = []
        polyline_parts: list[str] = []

        for i, step in enumerate(steps):
            seg_distance = _safe_float(step.get("distance", 0)) / 1000.0
            seg_duration = _safe_float(step.get("duration", 0)) / 60.0
            step_polyline = step.get("polyline", "")
            if step_polyline:
                polyline_parts.append(step_polyline)

            # Map step to nearest known POI
            from_name = "?"
            to_name = "?"
            if i < len(all_coords):
                from_name = f"stop_{i + 1}"
            if i + 1 < len(all_coords):
                to_name = f"stop_{i + 2}"

            segments.append({
                "from": from_name,
                "to": to_name,
                "distance_km": round(seg_distance, 2),
                "duration_min": round(seg_duration, 2),
            })

        polyline = ";".join(polyline_parts)

        return {
            "distance_km": round(distance_m / 1000.0, 2),
            "duration_min": round(duration_s / 60.0, 2),
            "polyline": polyline,
            "segments": segments,
        }
