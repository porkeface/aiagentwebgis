"""Progress tracker for the custom ReAct agent loop.

Tracks tool invocation progress and generates human-readable labels
for SSE progress events sent to the frontend.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProgressTracker:
    """Tracks tool invocation progress across the entire agent run.

    Labels are appended as the LLM decides to invoke tools across turns.
    The frontend sees (completed / total) updated in real time.
    """

    completed: int = 0
    labels: list[str] = field(default_factory=list)

    def add_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        """Record a pending tool invocation. Returns the label."""
        # tool_input may be a JSON string from the model's tool_call chunk
        if isinstance(tool_input, str):
            try:
                import json
                tool_input = json.loads(tool_input)
            except (json.JSONDecodeError, TypeError):
                tool_input = {}
        label = _tool_label(name, tool_input)
        self.labels.append(label)
        return label

    def mark_complete(self) -> dict[str, Any]:
        """Mark one tool as complete. Returns the SSE progress dict."""
        self.completed += 1
        total = max(len(self.labels), self.completed)
        return {
            "type": "progress",
            "data": {
                "step": self.completed,
                "total": total,
                "label": (
                    self.labels[self.completed - 1]
                    if self.completed <= len(self.labels)
                    else "处理中..."
                ),
            },
        }


def _tool_label(name: str, tool_input: dict[str, Any]) -> str:
    """Map a tool name + input to a human-readable Chinese label."""
    label_map = {
        "search_pois": f"正在搜索 {tool_input.get('city', '')} 的 {tool_input.get('category', '')}...",
        "search_nearby": "正在搜索周边...",
        "plan_route": "正在查询路线距离...",
        "plan_day_route": "正在规划每日最优路线...",
        "optimize_route": "正在优化访问顺序...",
        "score_pois": "正在评估 POI...",
        "submit_plan": "正在验证行程...",
        "geocode": "正在解析地址...",
        "reverse_geocode": "正在查询地址...",
        "get_weather": "正在查询天气...",
        "geo_partition": "正在按区域分组 POI...",
    }
    return label_map.get(name, f"正在 {name}...")
