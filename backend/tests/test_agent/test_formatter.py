"""Tests for Formatter Node (Task 2.4).

Tests cover:
- FormatterNode.format() produces correct SSE events
- poi_result event with center and zoom when candidate_pois present
- route_result event when daily_plans present
- plan_summary event when city and days present
- text event always emitted with response_text
- _calc_center calculates average lng/lat correctly
- _calc_center handles empty POI list with default center
- General intent produces text-only events (no poi_result)
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_base_state(**overrides) -> dict:
    """Create a minimal AgentState-compatible dict for testing.

    Returns a dict with all required fields populated with safe defaults.
    Any keyword overrides replace the defaults.
    """
    state: dict = {
        "messages": [],
        "session_id": "test-session-formatter",
        "intent": "general",
        "city": None,
        "days": None,
        "preferences": [],
        "companion_types": [],
        "budget_level": None,
        "candidate_pois": [],
        "selected_pois": [],
        "daily_plans": [],
        "route_polylines": [],
        "recommendation_weights": None,
        "response_text": "",
        "structured_plan": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# _calc_center tests
# ---------------------------------------------------------------------------


class TestCalcCenter:
    """Test FormatterNode._calc_center static method."""

    @pytest.fixture
    def formatter(self) -> "FormatterNode":
        """Create a FormatterNode instance for testing."""
        from agent.nodes.formatter import FormatterNode

        return FormatterNode()

    def test_calc_center_single_poi(self, formatter) -> None:
        """Single POI should return its lng/lat as center."""
        pois = [{"lng": 120.15, "lat": 30.28}]
        center = formatter._calc_center(pois)
        assert center == {"lng": 120.15, "lat": 30.28}

    def test_calc_center_multiple_pois(self, formatter) -> None:
        """Multiple POIs should return average lng/lat."""
        pois = [
            {"lng": 120.0, "lat": 30.0},
            {"lng": 121.0, "lat": 31.0},
            {"lng": 122.0, "lat": 32.0},
        ]
        center = formatter._calc_center(pois)
        assert center == {"lng": 121.0, "lat": 31.0}

    def test_calc_center_empty_list_returns_default(self, formatter) -> None:
        """Empty POI list should return default center (Beijing)."""
        center = formatter._calc_center([])
        assert center == {"lng": 116.4, "lat": 39.9}

    def test_calc_center_does_not_mutate_input(self, formatter) -> None:
        """_calc_center should not modify the input list."""
        pois = [{"lng": 120.0, "lat": 30.0}]
        original_pois = [{"lng": 120.0, "lat": 30.0}]
        formatter._calc_center(pois)
        assert pois == original_pois


# ---------------------------------------------------------------------------
# FormatterNode.format() tests
# ---------------------------------------------------------------------------


class TestFormatterProducesSSEEvents:
    """Test FormatterNode.format() produces correct SSE events."""

    @pytest.fixture
    def formatter(self) -> "FormatterNode":
        """Create a FormatterNode instance for testing."""
        from agent.nodes.formatter import FormatterNode

        return FormatterNode()

    async def test_formatter_produces_sse_events(self, formatter) -> None:
        """format() should return state with structured_plan containing text event."""
        state = _make_base_state(response_text="你好！有什么可以帮你的吗？")

        result = await formatter.format(state)

        events = result["structured_plan"]
        assert isinstance(events, list)
        assert len(events) >= 1

        # Must contain a text event
        text_events = [e for e in events if e["type"] == "text"]
        assert len(text_events) == 1
        assert text_events[0]["content"] == "你好！有什么可以帮你的吗？"

    async def test_formatter_includes_poi_result(self, formatter) -> None:
        """format() should emit poi_result event when candidate_pois present."""
        pois = [
            {"name": "西湖", "lng": 120.15, "lat": 30.25},
            {"name": "灵隐寺", "lng": 120.10, "lat": 30.24},
            {"name": "断桥", "lng": 120.16, "lat": 30.26},
        ]
        state = _make_base_state(
            response_text="为您推荐以下景点",
            candidate_pois=pois,
        )

        result = await formatter.format(state)

        events = result["structured_plan"]
        poi_events = [e for e in events if e["type"] == "poi_result"]
        assert len(poi_events) == 1

        poi_event = poi_events[0]
        assert poi_event["pois"] == pois
        assert len(poi_event["pois"]) == 3
        assert poi_event["zoom"] == 12
        # Center should be average of the 3 POIs
        assert poi_event["center"]["lng"] == pytest.approx(120.1367, abs=0.001)
        assert poi_event["center"]["lat"] == pytest.approx(30.25, abs=0.001)

    async def test_formatter_includes_route_result(self, formatter) -> None:
        """format() should emit route_result event when daily_plans present."""
        daily_plans = [
            {"day": 1, "pois": ["西湖", "灵隐寺"]},
            {"day": 2, "pois": ["断桥", "宋城"]},
        ]
        polylines = [
            {"day": 1, "coords": [[120.15, 30.25], [120.10, 30.24]]},
        ]
        state = _make_base_state(
            response_text="这是您的行程安排",
            daily_plans=daily_plans,
            route_polylines=polylines,
        )

        result = await formatter.format(state)

        events = result["structured_plan"]
        route_events = [e for e in events if e["type"] == "route_result"]
        assert len(route_events) == 1

        route_event = route_events[0]
        assert route_event["daily_plans"] == daily_plans
        assert route_event["polylines"] == polylines

    async def test_formatter_includes_plan_summary(self, formatter) -> None:
        """format() should emit plan_summary event when city and days present."""
        state = _make_base_state(
            response_text="杭州两日游规划完成",
            city="杭州",
            days=2,
        )

        result = await formatter.format(state)

        events = result["structured_plan"]
        summary_events = [e for e in events if e["type"] == "plan_summary"]
        assert len(summary_events) == 1
        assert summary_events[0]["city"] == "杭州"
        assert summary_events[0]["days"] == 2

    async def test_formatter_general_intent_text_only(self, formatter) -> None:
        """General intent with no POIs should produce only text event."""
        state = _make_base_state(
            intent="general",
            response_text="你好！我是旅行规划助手。",
            candidate_pois=[],
            daily_plans=[],
            city=None,
            days=None,
        )

        result = await formatter.format(state)

        events = result["structured_plan"]
        # Should have exactly one event: the text event
        poi_events = [e for e in events if e["type"] == "poi_result"]
        route_events = [e for e in events if e["type"] == "route_result"]
        summary_events = [e for e in events if e["type"] == "plan_summary"]
        text_events = [e for e in events if e["type"] == "text"]

        assert len(poi_events) == 0, "General intent should not produce poi_result"
        assert len(route_events) == 0, "No daily_plans should not produce route_result"
        assert len(summary_events) == 0, "No city/days should not produce plan_summary"
        assert len(text_events) == 1, "Should always produce text event"

    async def test_formatter_does_not_mutate_state(self, formatter) -> None:
        """format() should return a new state dict, not mutate the original."""
        state = _make_base_state(response_text="测试文本")
        original_structured_plan = state["structured_plan"]

        result = await formatter.format(state)

        # Original state should be unchanged
        assert state["structured_plan"] == original_structured_plan
        # Result should be a different dict
        assert result is not state

    async def test_formatter_full_trip_state(self, formatter) -> None:
        """Full trip state should produce all event types."""
        pois = [
            {"name": "西湖", "lng": 120.15, "lat": 30.25},
            {"name": "灵隐寺", "lng": 120.10, "lat": 30.24},
        ]
        daily_plans = [{"day": 1, "pois": ["西湖", "灵隐寺"]}]
        polylines = [{"day": 1, "coords": [[120.15, 30.25], [120.10, 30.24]]}]

        state = _make_base_state(
            intent="trip_planning",
            response_text="杭州两日游行程安排如下...",
            city="杭州",
            days=2,
            candidate_pois=pois,
            daily_plans=daily_plans,
            route_polylines=polylines,
        )

        result = await formatter.format(state)

        events = result["structured_plan"]
        event_types = [e["type"] for e in events]

        assert "poi_result" in event_types
        assert "route_result" in event_types
        assert "plan_summary" in event_types
        assert "text" in event_types
        # Should have exactly 4 events
        assert len(events) == 4
