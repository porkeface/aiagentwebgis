"""Amap (Gaode Map) API service for POI search, geocoding, and route planning.

Base URL: https://restapi.amap.com/v3
Docs: https://lbs.amap.com/api/webservice/summary
"""

from __future__ import annotations

import httpx
from typing import Any


AMAP_BASE_URL = "https://restapi.amap.com/v3"


class AmapService:
    """Async client for the Amap (Gaode) REST API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazily create and return the shared httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=AMAP_BASE_URL,
                timeout=10.0,
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
        """Send a GET request to the Amap API with automatic key injection.

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

        response = await client.get(endpoint, params=all_params)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        if data.get("status") != "1":
            info = data.get("info", "Unknown error")
            infocode = data.get("infocode", "")
            raise ValueError(
                f"Amap API error: {info} (code={infocode})"
            )
        return data

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
        params: dict[str, str] = {"city": city, "offset": str(limit)}
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
                    "amap_id": poi.get("id", ""),
                    "name": poi.get("name", ""),
                    "address": poi.get("address", ""),
                    "lng": lng,
                    "lat": lat,
                    "type": poi.get("type", ""),
                    "city": city_name,
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

        location_str = geocodes[0].get("location", "")
        if not location_str or "," not in location_str:
            raise ValueError(f"Invalid location in geocode response: {location_str!r}")

        parts = location_str.split(",")
        lng = float(parts[0])
        lat = float(parts[1])
        return (lng, lat)

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
        distance_m = float(path.get("distance", 0))
        duration_s = float(path.get("duration", 0))

        # Concatenate polylines from all steps
        steps = path.get("steps", [])
        polyline_parts = [step.get("polyline", "") for step in steps if step.get("polyline")]
        polyline = ";".join(polyline_parts)

        return {
            "distance_km": distance_m / 1000.0,
            "duration_min": duration_s / 60.0,
            "polyline": polyline,
        }
