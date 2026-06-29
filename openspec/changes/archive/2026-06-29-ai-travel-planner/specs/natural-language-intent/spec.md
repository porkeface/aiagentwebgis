# Capability: Natural Language Intent Parsing

## Overview

Extract structured travel parameters from user's natural language input using LLM-based intent recognition.

## Extraction Schema

```python
class ParsedIntent:
    intent: Literal["trip_planning", "poi_recommendation", "general"]
    city: str | None
    days: int | None
    preferences: list[str]         # ["自然风光", "美食", "历史文化"]
    companion_types: list[str]     # ["children", "elderly", "solo", "couple"]
    budget_level: int | None       # 1-5
    start_date: str | None         # YYYY-MM-DD or relative ("明天", "五一")
    transport_mode: str | None     # "walking" | "driving" | "transit"
    constraints: list[str]         # ["不想太累", "避开人多"]
```

## Multi-Turn Context Accumulation

- First turn: "去杭州玩两天" → city=杭州, days=2
- Second turn: "带老人和小孩" → companion_types=["elderly", "children"] (added to existing context)
- Third turn: "不要去太远的地方" → constraints=["不想太累"] (added, preferences refined)

The AgentState accumulates parsed parameters across turns. Each turn's parsed result is merged into existing state, not replaced.

## Acceptance Scenarios

1. "帮我规划杭州两日游，喜欢自然风景和美食" → city=杭州, days=2, preferences=[自然风光, 美食]
2. "五一带爸妈和孩子去厦门" → city=厦门, start_date=五一, companion_types=[elderly, children]
3. "只有半天时间，推荐附近值得去的地方" → days=0.5, intent=poi_recommendation
4. Multi-turn: "去成都" → "玩三天" → "预算中等" → city=成都, days=3, budget_level=3
