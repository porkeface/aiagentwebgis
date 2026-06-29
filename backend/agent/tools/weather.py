"""Weather tool function — placeholder for MVP.

Returns mock weather data. Will be replaced with a real weather API
(e.g. Amap weather or third-party) in a future task.
"""

from __future__ import annotations

from typing import Any


async def get_weather_tool(city: str) -> dict[str, Any]:
    """Get weather data for a city (placeholder).

    Args:
        city: City name, e.g. "北京".

    Returns:
        Dict with keys: city, temperature, condition, humidity.
    """
    return {
        "city": city,
        "temperature": 25,
        "condition": "晴",
        "humidity": 60,
    }
