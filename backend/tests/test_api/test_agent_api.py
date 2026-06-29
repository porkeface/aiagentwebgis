"""Tests for Agent Chat SSE API endpoint."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestAgentChatSSE:
    """Test POST /api/v1/agent/chat SSE endpoint."""

    @patch("app.api.v1.agent.build_graph")
    async def test_sse_stream_format(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that SSE stream returns correct event format."""
        # Arrange: mock graph to return structured_plan events
        mock_events = [
            {"type": "plan_summary", "city": "杭州", "days": 3},
            {"type": "text", "content": "这是一份杭州3日游攻略"},
        ]
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
        mock_build_graph.return_value = mock_graph

        # Act
        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "test-session-1", "message": "帮我规划杭州3日游"},
        )

        # Assert: SSE response
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        body = response.text
        lines = body.strip().split("\n")

        # Parse SSE events: each event has 'event:' and 'data:' lines
        events = []
        i = 0
        while i < len(lines):
            if lines[i].startswith("event: "):
                event_type = lines[i].replace("event: ", "")
                i += 1
                if i < len(lines) and lines[i].startswith("data: "):
                    data = json.loads(lines[i].replace("data: ", ""))
                    events.append({"event": event_type, "data": data})
            i += 1

        # Should have 2 message events + 1 done event
        assert len(events) == 3
        assert events[0]["event"] == "message"
        assert events[0]["data"]["type"] == "plan_summary"
        assert events[0]["data"]["data"]["city"] == "杭州"

        assert events[1]["event"] == "message"
        assert events[1]["data"]["type"] == "text"
        assert events[1]["data"]["data"]["content"] == "这是一份杭州3日游攻略"

        assert events[2]["event"] == "done"
        assert events[2]["data"] == {}

    @patch("app.api.v1.agent.build_graph")
    async def test_done_event_always_sent(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that done event is always sent at end of stream."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "structured_plan": [{"type": "text", "content": "hello"}]
        }
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1", "message": "hi"},
        )

        assert response.status_code == 200
        body = response.text
        # Last event must be 'done'
        assert "event: done\ndata: {}" in body

    @patch("app.api.v1.agent.build_graph")
    async def test_empty_structured_plan(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that empty structured_plan still sends done event."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"structured_plan": []}
        mock_build_graph.return_value = mock_graph

        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s2", "message": "hello"},
        )

        assert response.status_code == 200
        body = response.text
        # Should only have the done event
        assert "event: done\ndata: {}" in body

    @patch("app.api.v1.agent.build_graph")
    async def test_graph_invoked_with_correct_config(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that graph is invoked with correct session_id config."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "structured_plan": [{"type": "text", "content": "ok"}]
        }
        mock_build_graph.return_value = mock_graph

        await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "my-session", "message": "test message"},
        )

        # Verify ainvoke was called with correct initial state and config
        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args
        initial_state = call_args.args[0]
        config = call_args.kwargs["config"]

        assert initial_state["messages"] == [
            {"role": "user", "content": "test message"}
        ]
        assert initial_state["session_id"] == "my-session"
        assert config == {"configurable": {"thread_id": "my-session"}}

    async def test_missing_message_field(self, client: AsyncClient) -> None:
        """Test that missing message field returns 422."""
        response = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "s1"},
        )
        assert response.status_code == 422

    @patch("app.api.v1.agent.build_graph")
    async def test_session_id_defaults_to_uuid(
        self,
        mock_build_graph: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Test that missing session_id generates a UUID."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "structured_plan": [{"type": "text", "content": "ok"}]
        }
        mock_build_graph.return_value = mock_graph

        await client.post(
            "/api/v1/agent/chat",
            json={"message": "hello"},
        )

        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args
        initial_state = call_args.args[0]
        # session_id should be a non-empty string (UUID)
        assert isinstance(initial_state["session_id"], str)
        assert len(initial_state["session_id"]) > 0
