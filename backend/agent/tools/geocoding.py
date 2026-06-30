"""Geocoding tools — wrapped for LangChain ReAct agent."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
async def geocode(
    address: str,
    city: str = "",
) -> dict[str, float]:
    """将地址转换为经纬度坐标。

    Args:
        address: 地址字符串，如 "北京市东城区景山前街4号"
        city: 可选的城市名，用于消除歧义
    """
    from agent.tools import get_amap

    amap = get_amap()
    full_address = f"{city}{address}" if city else address
    lng, lat = await amap.geocode(full_address)
    return {"lng": lng, "lat": lat}


@tool
async def reverse_geocode(
    lng: float,
    lat: float,
) -> dict[str, str]:
    """将经纬度坐标反向转换为地址。

    Args:
        lng: 经度
        lat: 纬度
    """
    from agent.tools import get_amap

    amap = get_amap()
    return await amap.reverse_geocode(lng, lat)
