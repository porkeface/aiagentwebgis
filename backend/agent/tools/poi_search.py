"""POI search tools — wrapped for LangChain ReAct agent."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def search_pois(
    city: str,
    category: str,
    keyword: str = "",
) -> list[dict[str, Any]]:
    """搜索指定城市的 POI（景点/餐厅/购物等）。

    根据城市名称和类别搜索兴趣点。类别必须是 Amap POI 类型之一：
    风景名胜、博物馆、中餐厅、小吃快餐、购物中心、公园、动物园、展览馆、
    寺庙、历史建筑、海滩、游乐园、剧院、咖啡馆、酒吧、体育场馆、大学、酒店 等。

    Args:
        city: 城市名称，如 "北京"、"上海"
        category: Amap POI 类型，如 "风景名胜"、"中餐厅"、"博物馆"
        keyword: 可选的关键词进一步筛选，如 "故宫"
    """
    from agent.tools import get_amap

    amap = get_amap()
    try:
        return await amap.search_pois(city=city, category=category, keyword=keyword or None)
    except Exception as e:
        logger.warning(f"search_pois failed for {city}/{category}: {e}")
        return []


@tool
async def search_nearby(
    lng: float,
    lat: float,
    category: str,
    radius: int = 1000,
) -> list[dict[str, Any]]:
    """搜索某个坐标周边的 POI。

    想知道某个地点附近有什么时使用。适合查找景点周围的餐厅、酒店等。

    Args:
        lng: 中心点经度
        lat: 中心点纬度
        category: Amap POI 类型
        radius: 搜索半径（米），默认 1000
    """
    from agent.tools import get_amap

    amap = get_amap()
    try:
        return await amap.search_nearby(lng=lng, lat=lat, category=category, radius=radius)
    except Exception as e:
        logger.warning(f"search_nearby failed for ({lng},{lat}): {e}")
        return []
