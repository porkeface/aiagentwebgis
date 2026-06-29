"""Tests for Router Node and AgentState (Task 2.1).

Tests cover:
- AgentState TypedDict has all required fields
- RouterNode intent classification (trip_planning, poi_recommendation, general)
- LangGraph build_graph() compiles successfully
- Router conditional edges route correctly
"""

import pytest
from typing import get_type_hints


# ---------------------------------------------------------------------------
# AgentState structure tests
# ---------------------------------------------------------------------------


class TestAgentState:
    """Test AgentState TypedDict definition."""

    def test_agent_state_has_required_fields(self) -> None:
        """AgentState should have all required fields defined."""
        from agent.state import AgentState

        hints = get_type_hints(AgentState)

        required_fields = [
            "messages",
            "session_id",
            "intent",
            "city",
            "days",
            "preferences",
            "companion_types",
            "budget_level",
            "candidate_pois",
            "selected_pois",
            "daily_plans",
            "route_polylines",
            "recommendation_weights",
            "response_text",
            "structured_plan",
        ]

        for field in required_fields:
            assert field in hints, f"AgentState missing field: {field}"

    def test_agent_state_field_count(self) -> None:
        """AgentState should have exactly 15 fields."""
        from agent.state import AgentState

        hints = get_type_hints(AgentState)
        assert len(hints) == 15


# ---------------------------------------------------------------------------
# RouterNode classification tests
# ---------------------------------------------------------------------------


class TestRouterClassification:
    """Test RouterNode's _classify_intent method."""

    @pytest.fixture
    def router(self) -> "RouterNode":
        """Create a RouterNode instance for testing."""
        from agent.nodes.router import RouterNode
        return RouterNode()

    def test_router_classifies_trip_planning(self, router) -> None:
        """Router should classify trip planning intent from Chinese keywords."""
        test_cases = [
            "帮我规划杭州两日游",
            "我想去北京旅行",
            "安排一个上海三日游行程",
            "计划去成都旅游",
            "帮我做个南京一日游的规划",
        ]
        for text in test_cases:
            intent = router._classify_intent(text)
            assert intent == "trip_planning", f"Failed for: {text}"

    def test_router_classifies_poi_recommendation(self, router) -> None:
        """Router should classify POI recommendation intent."""
        test_cases = [
            "杭州有什么好吃的",
            "推荐几个好玩的景点",
            "北京美食攻略",
            "上海有哪些值得去的景点",
            "成都好玩吗",
        ]
        for text in test_cases:
            intent = router._classify_intent(text)
            assert intent == "poi_recommendation", f"Failed for: {text}"

    def test_router_classifies_general(self, router) -> None:
        """Router should classify general/greeting intent."""
        test_cases = [
            "你好",
            "嗨",
            "hello",
            "hi",
            "你是谁",
        ]
        for text in test_cases:
            intent = router._classify_intent(text)
            assert intent == "general", f"Failed for: {text}"

    def test_router_empty_text_returns_general(self, router) -> None:
        """Empty text should be classified as general."""
        intent = router._classify_intent("")
        assert intent == "general"

    def test_router_trip_keywords_take_priority_over_poi(self, router) -> None:
        """When text contains both trip and POI keywords, trip_planning takes priority."""
        text = "帮我规划行程，推荐一些好吃的"
        intent = router._classify_intent(text)
        assert intent == "trip_planning"


# ---------------------------------------------------------------------------
# RouterNode route() method tests
# ---------------------------------------------------------------------------


class TestRouterRoute:
    """Test RouterNode's route method updates state correctly."""

    @pytest.fixture
    def router(self) -> "RouterNode":
        """Create a RouterNode instance for testing."""
        from agent.nodes.router import RouterNode
        return RouterNode()

    def test_route_sets_intent_in_state(self, router) -> None:
        """route() should return new state with intent field set."""
        from agent.state import AgentState

        initial_state: AgentState = {
            "messages": [{"role": "user", "content": "帮我规划杭州两日游"}],
            "session_id": "test-session-1",
            "intent": "",
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

        result = router.route(initial_state)

        assert result["intent"] == "trip_planning"
        # Other fields should remain unchanged
        assert result["session_id"] == "test-session-1"
        assert result["messages"] == initial_state["messages"]

    def test_route_does_not_mutate_original_state(self, router) -> None:
        """route() should not mutate the original state (immutable pattern)."""
        from agent.state import AgentState

        initial_state: AgentState = {
            "messages": [{"role": "user", "content": "你好"}],
            "session_id": "test-session-2",
            "intent": "",
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

        original_intent = initial_state["intent"]
        router.route(initial_state)

        # Original state should not be mutated
        assert initial_state["intent"] == original_intent


# ---------------------------------------------------------------------------
# Graph build tests
# ---------------------------------------------------------------------------


class TestBuildGraph:
    """Test build_graph() function."""

    def test_build_graph_compiles(self) -> None:
        """build_graph() should return a compiled graph."""
        from agent.graph import build_graph

        graph = build_graph()
        assert graph is not None

    def test_build_graph_has_nodes(self) -> None:
        """Compiled graph should contain router, planner, formatter nodes."""
        from agent.graph import build_graph

        graph = build_graph()
        # LangGraph compiled graph has a .nodes attribute
        node_names = set(graph.get_graph().nodes.keys())
        assert "router" in node_names
        assert "planner" in node_names
        assert "formatter" in node_names

    async def test_graph_routes_trip_to_planner(self) -> None:
        """Trip planning input should route through planner."""
        from unittest.mock import AsyncMock, patch

        from agent.graph import build_graph
        from agent.llm.base import LLMResponse
        from agent.state import AgentState

        # Mock the LLM adapter to avoid real API calls
        mock_adapter = AsyncMock()
        mock_adapter.chat = AsyncMock(
            return_value=LLMResponse(content="杭州两日游行程安排...")
        )

        with patch("agent.graph.get_llm_adapter", return_value=mock_adapter):
            graph = build_graph()

            initial_state: AgentState = {
                "messages": [{"role": "user", "content": "帮我规划杭州两日游"}],
                "session_id": "test-session-1",
                "intent": "",
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

            # Planner is now async, so use ainvoke
            result = await graph.ainvoke(initial_state)
            # After routing through planner and formatter, intent should be set
            assert result["intent"] == "trip_planning"
            # Planner should have extracted city and days
            assert result["city"] == "杭州"
            assert result["days"] == 2
            # Planner should have populated recommendation_weights
            assert result["recommendation_weights"] is not None
            # Planner should have set response_text
            assert result["response_text"] != ""

    async def test_graph_routes_general_to_formatter(self) -> None:
        """General/greeting input should route directly to formatter."""
        from agent.graph import build_graph
        from agent.state import AgentState

        graph = build_graph()

        initial_state: AgentState = {
            "messages": [{"role": "user", "content": "你好"}],
            "session_id": "test-session-2",
            "intent": "",
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

        result = await graph.ainvoke(initial_state)
        assert result["intent"] == "general"
