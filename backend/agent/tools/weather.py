"""Weather tool — wrapped for LangChain ReAct agent.

Returns mock weather data.  Will be replaced with a real weather API in the future.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
async def get_weather(city: str) -> dict[str, Any]:
    """查询城市天气（当前为模拟数据，仅供参考）。

    Args:
        city: 城市名称，如 "北京"
    """
    return {
        "city": city,
        "temperature": 25,
        "condition": "晴",
        "humidity": 60,
    }
