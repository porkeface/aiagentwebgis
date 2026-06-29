"""Tests for Planner Node (Task 2.3).

Tests cover:
- PlannerNode produces response_text after plan()
- City extraction from user messages
- Default weight population based on companion_types
"""

import pytest
from unittest.mock import AsyncMock

from agent.llm.base import BaseLLMAdapter, LLMResponse
from agent.nodes.planner import PlannerNode
from agent.state import AgentState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> AgentState:
    """Create a minimal valid AgentState with optional overrides."""
    base: AgentState = {
        "messages": [{"role": "user", "content": "帮我规划杭州两日游"}],
        "session_id": "test-session-1",
        "intent": "trip_planning",
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
    base.update(overrides)
    return base


@pytest.fixture
def mock_adapter() -> BaseLLMAdapter:
    """Create a mock LLM adapter that returns a fixed response."""
    adapter = AsyncMock(spec=BaseLLMAdapter)
    adapter.chat = AsyncMock(
        return_value=LLMResponse(
            content="好的，我为您规划杭州两日游行程：\n第一天：西湖、灵隐寺\n第二天：宋城、河坊街",
            tool_calls=[],
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )
    )
    return adapter


@pytest.fixture
def planner(mock_adapter: BaseLLMAdapter) -> PlannerNode:
    """Create a PlannerNode with mock adapter."""
    return PlannerNode(llm_adapter=mock_adapter)


# ---------------------------------------------------------------------------
# Test: planner produces response_text
# ---------------------------------------------------------------------------


class TestPlannerResponse:
    """Test that planner calls LLM and sets response_text."""

    @pytest.mark.asyncio
    async def test_planner_produces_response_text(
        self, planner: PlannerNode, mock_adapter: BaseLLMAdapter
    ) -> None:
        """plan() should set response_text from LLM response content."""
        state = _make_state()
        result = await planner.plan(state)

        assert result["response_text"] != ""
        assert "杭州" in result["response_text"]
        mock_adapter.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_planner_does_not_mutate_original(
        self, planner: PlannerNode
    ) -> None:
        """plan() should return a new state dict, not mutate the original."""
        state = _make_state()
        original_response = state["response_text"]

        await planner.plan(state)

        assert state["response_text"] == original_response


# ---------------------------------------------------------------------------
# Test: city extraction
# ---------------------------------------------------------------------------


class TestPlannerExtraction:
    """Test _extract_params extracts city and days from messages."""

    @pytest.fixture
    def planner(self, mock_adapter: BaseLLMAdapter) -> PlannerNode:
        return PlannerNode(llm_adapter=mock_adapter)

    def test_planner_extracts_city_hangzhou(self, planner: PlannerNode) -> None:
        """Should extract '杭州' from '帮我规划杭州两日游'."""
        state = _make_state(
            messages=[{"role": "user", "content": "帮我规划杭州两日游"}]
        )
        params = planner._extract_params(state)
        assert params["city"] == "杭州"

    def test_planner_extracts_days_from_chinese(self, planner: PlannerNode) -> None:
        """Should extract days=2 from '两日'."""
        state = _make_state(
            messages=[{"role": "user", "content": "帮我规划杭州两日游"}]
        )
        params = planner._extract_params(state)
        assert params["days"] == 2

    def test_planner_extracts_days_from_arabic(self, planner: PlannerNode) -> None:
        """Should extract days=3 from '3天'."""
        state = _make_state(
            messages=[{"role": "user", "content": "北京3天行程"}]
        )
        params = planner._extract_params(state)
        assert params["days"] == 3
        assert params["city"] == "北京"

    def test_planner_extracts_known_city(self, planner: PlannerNode) -> None:
        """Should extract known city '上海' from message."""
        state = _make_state(
            messages=[{"role": "user", "content": "上海有什么好玩的"}]
        )
        params = planner._extract_params(state)
        assert params["city"] == "上海"

    def test_planner_extract_returns_none_for_no_match(
        self, planner: PlannerNode
    ) -> None:
        """Should return None for city/days when no pattern matches."""
        state = _make_state(
            messages=[{"role": "user", "content": "你好"}]
        )
        params = planner._extract_params(state)
        assert params["city"] is None
        assert params["days"] is None

    def test_planner_extracts_from_last_user_message(
        self, planner: PlannerNode
    ) -> None:
        """Should extract from the last user message, not earlier ones."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "北京三日游"},
                {"role": "assistant", "content": "好的，北京三日游..."},
                {"role": "user", "content": "改成上海两天"},
            ]
        )
        params = planner._extract_params(state)
        assert params["city"] == "上海"
        assert params["days"] == 2


# ---------------------------------------------------------------------------
# Test: default weights
# ---------------------------------------------------------------------------


class TestPlannerWeights:
    """Test _ensure_weights sets appropriate defaults."""

    @pytest.fixture
    def planner(self, mock_adapter: BaseLLMAdapter) -> PlannerNode:
        return PlannerNode(llm_adapter=mock_adapter)

    def test_planner_sets_default_weights(self, planner: PlannerNode) -> None:
        """Should set default weights when recommendation_weights is None."""
        state = _make_state(recommendation_weights=None, companion_types=[])
        result = planner._ensure_weights(state)

        weights = result["recommendation_weights"]
        assert weights is not None
        assert "preference" in weights
        assert "distance" in weights
        assert "rating" in weights
        assert "time" in weights
        assert "popularity" in weights

    def test_default_weights_sum_approximately_one(
        self, planner: PlannerNode
    ) -> None:
        """Default weights should sum to approximately 1.0."""
        state = _make_state(recommendation_weights=None, companion_types=[])
        result = planner._ensure_weights(state)
        total = sum(result["recommendation_weights"].values())
        assert abs(total - 1.0) < 0.01

    def test_elderly_companion_adjusts_weights(
        self, planner: PlannerNode
    ) -> None:
        """Elderly companion should lower distance and time."""
        state = _make_state(
            recommendation_weights=None, companion_types=["elderly"]
        )
        result = planner._ensure_weights(state)
        weights = result["recommendation_weights"]

        assert weights["distance"] == 0.15
        assert weights["time"] == 0.25

    def test_children_companion_adjusts_weights(
        self, planner: PlannerNode
    ) -> None:
        """Children companion should increase popularity."""
        state = _make_state(
            recommendation_weights=None, companion_types=["children"]
        )
        result = planner._ensure_weights(state)
        weights = result["recommendation_weights"]

        assert weights["distance"] == 0.15
        assert weights["popularity"] == 0.30

    def test_existing_weights_not_overwritten(
        self, planner: PlannerNode
    ) -> None:
        """Should not overwrite weights that are already set."""
        custom_weights = {"preference": 0.5, "distance": 0.5}
        state = _make_state(
            recommendation_weights=custom_weights, companion_types=[]
        )
        result = planner._ensure_weights(state)
        assert result["recommendation_weights"] == custom_weights
