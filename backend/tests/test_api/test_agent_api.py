"""Tests for Agent Chat SSE API endpoint."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from langchain_core.messages import AIMessageChunk


def _make_gen(events: list[dict]):
    """Return a bare async generator (not wrapped in another async def)."""
    async def _gen():
        for ev in events:
            ev_type = ev.get("type", "text")
            if ev_type == "text":
                content = ev.get("content", "")
                yield {"event": "on_chat_model_start", "data": {}}
                for ch in content:
                    yield {
                        "event": "on_chat_model_stream",
                        "data": {"chunk": AIMessageChunk(content=ch)},
                    }
            elif ev_type == "plan_summary":
                yield {
                    "event": "on_custom_event",
                    "name": "plan_summary",
                    "data": {"city": ev.get("city", ""), "days": ev.get("days", 0)},
                }
    return _gen()


class TestAgentChatSSE:
    """Test POST /api/v1/agent/chat SSE endpoint."""

    @patch("app.api.v1.agent.build_graph_v2")
    async def test_sse_stream_format(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that SSE stream returns correct event format."""
        mock_graph = AsyncMock()
        mock_graph.astream_events = lambda *a, **kw: _make_gen([
            {"type": "text", "content": "hello"},
        ])
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "test-session-1", "message": "hi"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.text
        assert "event: done\ndata: {}" in body

    @patch("app.api.v1.agent.build_graph_v2")
    async def test_done_event_always_sent(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that done event is always sent at end of stream."""
        mock_graph = AsyncMock()
        mock_graph.astream_events = lambda *a, **kw: _make_gen(
            [{"type": "text", "content": "hello"}]
        )
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "hi"},
        )

        assert response.status_code == 200
        body = response.text
        assert "event: done\ndata: {}" in body

    @patch("app.api.v1.agent.build_graph_v2")
    async def test_empty_structured_plan(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that an empty graph still sends done event."""
        mock_graph = AsyncMock()

        async def _empty():
            return
            yield  # pragma: no cover

        mock_graph.astream_events = lambda *a, **kw: _empty()
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s2", "message": "hello"},
        )

        assert response.status_code == 200
        body = response.text
        assert "event: done\ndata: {}" in body

    @patch("app.api.v1.agent.build_graph_v2")
    async def test_graph_invoked_with_correct_config(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that agent endpoint works with session_id config."""
        mock_graph = AsyncMock()
        mock_graph.astream_events = lambda *a, **kw: _make_gen(
            [{"type": "text", "content": "ok"}]
        )
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "my-session", "message": "test message"},
        )

        assert response.status_code == 200
        assert "event: done" in response.text

    async def test_missing_message_field(self, client: AsyncClient) -> None:
        """Test that missing message field returns 422."""
        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1"},
        )
        assert response.status_code == 422

    @patch("app.api.v1.agent.build_graph_v2")
    async def test_session_id_defaults_to_uuid(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that missing session_id still works."""
        mock_graph = AsyncMock()
        mock_graph.astream_events = lambda *a, **kw: _make_gen(
            [{"type": "text", "content": "ok"}]
        )
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"message": "hello"},
        )

        assert response.status_code == 200
        assert "event: done" in response.text
