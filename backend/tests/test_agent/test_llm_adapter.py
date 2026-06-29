"""Tests for LLM Adapter Layer (Task 1.4).

Tests cover:
- Dataclass structures (ToolCall, LLMResponse, LLMChunk)
- TongyiAdapter prompt parsing and tool formatting
- Factory pattern for adapter selection
- Mock langchain chat models (no real API calls)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from agent.llm.base import (
    ToolCall,
    LLMResponse,
    LLMChunk,
    BaseLLMAdapter,
)
from agent.llm.factory import get_llm_adapter


# ---------------------------------------------------------------------------
# Dataclass structure tests
# ---------------------------------------------------------------------------


class TestDataclassStructures:
    """Test dataclass definitions and their immutability."""

    def test_tool_call_structure(self) -> None:
        """ToolCall should have id, name, arguments fields."""
        tc = ToolCall(
            id="call_123",
            name="search_pois",
            arguments={"city": "北京", "keyword": "故宫"}
        )
        assert tc.id == "call_123"
        assert tc.name == "search_pois"
        assert tc.arguments == {"city": "北京", "keyword": "故宫"}

    def test_tool_call_frozen(self) -> None:
        """ToolCall should be immutable (frozen=True)."""
        tc = ToolCall(id="call_123", name="test", arguments={})
        with pytest.raises(Exception):  # FrozenInstanceError
            tc.id = "changed"  # type: ignore

    def test_llm_response_structure(self) -> None:
        """LLMResponse should have content, tool_calls, usage."""
        tc1 = ToolCall(id="call_1", name="tool1", arguments={"arg": "val1"})
        tc2 = ToolCall(id="call_2", name="tool2", arguments={"arg": "val2"})

        response = LLMResponse(
            content="Here are the results",
            tool_calls=[tc1, tc2],
            usage={"prompt_tokens": 100, "completion_tokens": 50}
        )

        assert response.content == "Here are the results"
        assert len(response.tool_calls) == 2
        assert response.tool_calls[0].name == "tool1"
        assert response.usage["prompt_tokens"] == 100

    def test_llm_response_frozen(self) -> None:
        """LLMResponse should be immutable."""
        response = LLMResponse(content="test", tool_calls=[], usage={})
        with pytest.raises(Exception):
            response.content = "changed"  # type: ignore

    def test_llm_chunk_structure(self) -> None:
        """LLMChunk should have content, tool_call_delta, is_done."""
        chunk = LLMChunk(
            content="partial text",
            tool_call_delta=None,
            is_done=False
        )
        assert chunk.content == "partial text"
        assert chunk.tool_call_delta is None
        assert chunk.is_done is False

    def test_llm_chunk_final(self) -> None:
        """Final chunk should have is_done=True."""
        final_chunk = LLMChunk(
            content="",
            tool_call_delta=None,
            is_done=True
        )
        assert final_chunk.is_done is True


# ---------------------------------------------------------------------------
# TongyiAdapter parsing tests
# ---------------------------------------------------------------------------


class TestTongyiAdapterParsing:
    """Test TongyiAdapter's prompt-based fallback parsing."""

    @pytest.fixture
    def tongyi_adapter(self) -> "TongyiAdapter":
        """Create a TongyiAdapter instance for testing."""
        from agent.llm.tongyi import TongyiAdapter
        return TongyiAdapter(api_key="test_key")

    def test_format_tools_as_prompt(self, tongyi_adapter) -> None:
        """_format_tools_as_prompt should convert tool schemas to text."""
        tools = [
            {
                "name": "search_pois",
                "description": "Search for points of interest",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                        "keyword": {"type": "string", "description": "Search keyword"}
                    },
                    "required": ["city", "keyword"]
                }
            }
        ]

        prompt = tongyi_adapter._format_tools_as_prompt(tools)

        # Should contain tool name
        assert "search_pois" in prompt
        # Should contain description
        assert "Search for points of interest" in prompt
        # Should contain parameter names
        assert "city" in prompt
        assert "keyword" in prompt

    def test_parse_tool_calls_from_json_text(self, tongyi_adapter) -> None:
        """_parse_tool_calls_from_text should extract JSON with 'tool' and 'args'."""
        text = """
        I will search for POIs in Beijing.
        {"tool": "search_pois", "args": {"city": "北京", "keyword": "故宫"}}
        That should give us good results.
        """

        tool_calls = tongyi_adapter._parse_tool_calls_from_text(text)

        assert len(tool_calls) == 1
        assert tool_calls[0].name == "search_pois"
        assert tool_calls[0].arguments == {"city": "北京", "keyword": "故宫"}
        assert tool_calls[0].id is not None  # Should have auto-generated ID

    def test_parse_tool_calls_multiple(self, tongyi_adapter) -> None:
        """_parse_tool_calls_from_text should handle multiple tool calls."""
        text = """
        First tool:
        {"tool": "search_pois", "args": {"city": "北京"}}
        Second tool:
        {"tool": "geocode", "args": {"address": "故宫"}}
        """

        tool_calls = tongyi_adapter._parse_tool_calls_from_text(text)

        assert len(tool_calls) == 2
        assert tool_calls[0].name == "search_pois"
        assert tool_calls[1].name == "geocode"

    def test_parse_tool_calls_handles_no_json(self, tongyi_adapter) -> None:
        """_parse_tool_calls_from_text should return [] when no JSON found."""
        text = "This is just plain text with no JSON at all."

        tool_calls = tongyi_adapter._parse_tool_calls_from_text(text)

        assert tool_calls == []

    def test_parse_tool_calls_handles_invalid_json(self, tongyi_adapter) -> None:
        """_parse_tool_calls_from_text should skip invalid JSON gracefully."""
        text = """
        Valid: {"tool": "search_pois", "args": {"city": "北京"}}
        Invalid: {"tool": "geocode", "args": missing_quotes}
        """

        tool_calls = tongyi_adapter._parse_tool_calls_from_text(text)

        # Should only parse the valid one
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "search_pois"


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestFactory:
    """Test get_llm_adapter() factory function."""

    def test_factory_returns_tongyi(self) -> None:
        """get_llm_adapter('dashscope') should return TongyiAdapter."""
        from agent.llm.tongyi import TongyiAdapter

        with patch.dict("os.environ", {"LLM_PROVIDER": "dashscope"}):
            adapter = get_llm_adapter()

        assert isinstance(adapter, TongyiAdapter)

    def test_factory_returns_openai(self) -> None:
        """get_llm_adapter('openai') should return OpenAIAdapter."""
        from agent.llm.openai_adapter import OpenAIAdapter

        with patch.dict("os.environ", {"LLM_PROVIDER": "openai"}):
            adapter = get_llm_adapter()

        assert isinstance(adapter, OpenAIAdapter)

    def test_factory_returns_ollama(self) -> None:
        """get_llm_adapter('ollama') should return OllamaAdapter."""
        from agent.llm.ollama import OllamaAdapter

        with patch.dict("os.environ", {"LLM_PROVIDER": "ollama"}):
            adapter = get_llm_adapter()

        assert isinstance(adapter, OllamaAdapter)

    def test_factory_unknown_provider_raises(self) -> None:
        """get_llm_adapter with unknown provider should raise ValueError."""
        with patch.dict("os.environ", {"LLM_PROVIDER": "unknown"}):
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_llm_adapter()

    def test_factory_reads_config(self) -> None:
        """Factory should read from app.config.settings."""
        from agent.llm.tongyi import TongyiAdapter

        with patch("app.config.settings") as mock_settings:
            mock_settings.llm_provider = "dashscope"
            mock_settings.dashscope_api_key = "test_key"
            adapter = get_llm_adapter()

        assert isinstance(adapter, TongyiAdapter)
