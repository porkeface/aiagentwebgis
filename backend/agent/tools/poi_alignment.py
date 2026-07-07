"""POI name alignment — LLM selects the best match from multiple Amap candidates.

When searching a guide-extracted spot name on Amap, the API often returns
multiple candidates (different entrances, nearby shops, bus stops, etc.).
This module uses a fast LLM call to pick the real tourist attraction.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

ALIGN_PROMPT = """你是一个精确的POI名称匹配器。用户想找一个景点，高德API返回了多个候选。
请从候选中选出**真正是旅游景点**的那一个（而不是公交站、停车场、分店等）。

规则：
1. 优先选旅游景点类（风景名胜、博物馆、公园等），排除公交站/停车场/售票处/出口入口
2. 如果多个候选都是景点，选评分最高、评论数最多的主馆/主入口
3. 如果用户说了具体位置（如"故宫"），选核心的那个，不要选侧门/后门
4. 如果没有合适的候选（全是公交站/停车场等），返回 null

返回纯JSON（不要markdown代码块）：
{"selected_index": <候选在列表中的索引 或 -1表示无合适结果>, "reason": "<选择理由>"}"""


def _build_poi_summary(poi: dict[str, Any], idx: int) -> str:
    """Build a one-line summary of a POI candidate for LLM consumption."""
    parts = [f"[{idx}] {poi.get('name', '?')}"]
    addr = poi.get("address", "")
    if addr:
        parts.append(f"地址: {addr}")
    cat = poi.get("category") or poi.get("type", "")
    if cat:
        parts.append(f"类型: {cat}")
    rating = poi.get("rating")
    if rating and isinstance(rating, (int, float)) and rating > 0:
        parts.append(f"评分: {rating}")
    review = poi.get("review_count")
    if review and isinstance(review, (int, float)) and review > 0:
        parts.append(f"评论数: {review}")
    biz_area = poi.get("business_area", "")
    if biz_area:
        parts.append(f"商圈: {biz_area}")
    importance = poi.get("importance", "")
    if importance:
        parts.append(f"等级: {importance}")
    return " | ".join(parts)


def _filter_by_type(poi: dict[str, Any]) -> bool:
    """Quick pre-filter: exclude obvious non-attractions."""
    cat = (poi.get("category") or poi.get("type") or "").lower()
    name = (poi.get("name") or "").lower()
    exclude_keywords = [
        "公交站", "停车场", "售票处", "出口", "入口", "卫生间",
        "地铁站", "atm", "加油站", "收费站", "服务区",
    ]
    for kw in exclude_keywords:
        if kw in name or kw in cat:
            return False
    return True


async def align_poi_name(
    target_name: str,
    candidates: list[dict[str, Any]],
    context: str = "",
) -> dict[str, Any] | None:
    """Pick the best Amap POI match for a guide-extracted spot name.

    Args:
        target_name: The spot name from a guide (e.g. "故宫").
        candidates: Raw Amap search results for this name.
        context: Optional extra context (city, guide tips, etc.).

    Returns:
        The best-matching POI dict, or None if no good match.
    """
    if not candidates:
        return None

    # Pre-filter
    filtered = [p for p in candidates if _filter_by_type(p)]
    if not filtered:
        filtered = candidates  # fallback to all

    # Single candidate with high confidence is safe
    if len(filtered) == 1:
        return filtered[0]

    # Fast path: the first result has high rating + is a scenic type
    first = filtered[0]
    first_cat = first.get("category") or first.get("type") or ""
    first_rating = first.get("rating") or 0
    if (
        len(filtered) == 1
        or (first_rating >= 4.0 and any(t in first_cat for t in ["风景名胜", "博物馆", "公园", "寺庙", "历史"]))
    ):
        if len(filtered) == 1 or not any(
            p.get("name") != first.get("name") and (p.get("rating") or 0) > first_rating
            for p in filtered[1:4]
        ):
            return first

    # LLM alignment for ambiguous cases
    summaries = "\n".join(_build_poi_summary(p, i) for i, p in enumerate(filtered[:8]))
    user_msg = f"目标景点：{target_name}\n{context}\n\n候选列表：\n{summaries}"

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0.0,
            timeout=20,
            max_retries=1,
        )
        response = await model.ainvoke([
            SystemMessage(content=ALIGN_PROMPT),
            HumanMessage(content=user_msg),
        ])
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rstrip("```").strip()

        result = json.loads(content)
        idx = result.get("selected_index", -1)
        reason = result.get("reason", "LLM未提供理由")
        if idx >= 0 and idx < len(filtered):
            logger.info("POI alignment for '%s': selected [%d] %s — %s",
                        target_name, idx, filtered[idx].get("name"), reason)
            return filtered[idx]
        else:
            logger.info("POI alignment for '%s': no good match among %d candidates", target_name, len(filtered))
            return None
    except Exception:
        logger.warning("POI alignment LLM call failed for '%s', falling back to first candidate", target_name)
        return filtered[0] if filtered else None
