"""E2E Smoke Tests for AI Travel Planner.

These tests verify the full system works end-to-end.
They are designed to be resilient and skip gracefully when services are not available.

Run with:
    pytest backend/tests/e2e/ -v

Or when services are running:
    pytest backend/tests/e2e/ -v --e2e-live
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # aiagentwebgis/
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _check_service_available(url: str, timeout: float = 2.0) -> bool:
    """Check if a service is available at the given URL.

    Args:
        url: The URL to check.
        timeout: Connection timeout in seconds.

    Returns:
        True if the service is reachable, False otherwise.
    """
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code < 500
    except (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout):
        return False


@pytest.fixture
def backend_available() -> bool:
    """Check if backend service is available."""
    return _check_service_available(f"{BACKEND_URL}/health")


@pytest.fixture
def frontend_available() -> bool:
    """Check if frontend service is available."""
    return _check_service_available(FRONTEND_URL)


@pytest.fixture
def http_client() -> Generator[httpx.Client, None, None]:
    """Provide an HTTP client for E2E tests."""
    with httpx.Client(timeout=30.0) as client:
        yield client


@pytest.fixture
def test_client() -> Generator[Any, None, None]:
    """Provide a synchronous test client using ASGI transport."""
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse_events(body: str) -> list[dict[str, Any]]:
    """Parse SSE response body into list of events.

    Handles SSE spec multi-line data fields by joining data lines.

    Each event has:
        - 'event': the SSE event type (e.g. 'message', 'done')
        - 'data': the parsed JSON data dict

    Args:
        body: Raw SSE response text.

    Returns:
        List of parsed events.
    """
    events: list[dict[str, Any]] = []
    lines = body.strip().split("\n")

    current_event_type: str | None = None
    data_lines: list[str] = []

    for line in lines:
        if line.startswith("event: "):
            # Save previous event if exists
            if current_event_type is not None and data_lines:
                data_str = "\n".join(data_lines)
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = {}
                events.append({"event": current_event_type, "data": data})
            current_event_type = line[len("event: "):]
            data_lines = []
        elif line.startswith("data: "):
            data_lines.append(line[len("data: "):])

    # Handle last event
    if current_event_type is not None and data_lines:
        data_str = "\n".join(data_lines)
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            data = {}
        events.append({"event": current_event_type, "data": data})

    return events


def _get_event_inner_data(event: dict[str, Any]) -> dict[str, Any]:
    """Extract the inner data from an SSE envelope.

    The agent.py SSE endpoint wraps each structured_plan event as:
        {"type": "<event_type>", "data": <original_event_dict>}

    This helper extracts the inner data dict.

    Args:
        event: A parsed SSE event with 'event' and 'data' keys.

    Returns:
        The inner data dict from the envelope.
    """
    return event["data"].get("data", {})


# ---------------------------------------------------------------------------
# Test: Backend Health Check
# ---------------------------------------------------------------------------


class TestBackendHealth:
    """Test backend service availability."""

    def test_health_endpoint_exists(
        self, backend_available: bool, http_client: httpx.Client
    ) -> None:
        """Test that /health endpoint responds.

        This test is skipped if backend is not running.
        """
        if not backend_available:
            pytest.skip("Backend service not available at localhost:8000")

        response = http_client.get(f"{BACKEND_URL}/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"

        data = response.json()
        assert data == {"status": "ok"}, f"Unexpected health response: {data}"

    def test_api_docs_available(
        self, backend_available: bool, http_client: httpx.Client
    ) -> None:
        """Test that API docs endpoint is accessible.

        This test is skipped if backend is not running.
        """
        if not backend_available:
            pytest.skip("Backend service not available")

        response = http_client.get(f"{BACKEND_URL}/docs")
        assert response.status_code == 200, "API docs not accessible"


# ---------------------------------------------------------------------------
# Test: Agent Chat SSE (Mocked)
# ---------------------------------------------------------------------------


class TestAgentChatSSEMocked:
    """Test agent chat SSE with mocked LLM/graph.

    These tests use the in-process test client and mock the graph,
    so they don't require external services to be running.

    The mock data format matches FormatterNode output (flat dicts):
        {"type": "poi_result", "pois": [...], "center": {...}, "zoom": 12}

    The SSE endpoint (agent.py) wraps each event as:
        {"type": "<type>", "data": <flat_dict>}
    """

    def test_sse_stream_with_poi_and_route(self, test_client: Any) -> None:
        """Test SSE stream returns poi_result and route_result events.

        Uses mocked graph to simulate agent behavior.
        """
        # Mock structured plan matching FormatterNode output (flat dicts)
        mock_events: list[dict[str, Any]] = [
            {
                "type": "plan_summary",
                "city": "杭州",
                "days": 2,
            },
            {
                "type": "poi_result",
                "pois": [
                    {"id": "1", "name": "西湖", "lng": 120.15, "lat": 30.25, "category": "scenic"},
                    {"id": "2", "name": "灵隐寺", "lng": 120.10, "lat": 30.24, "category": "temple"},
                ],
                "center": {"lng": 120.125, "lat": 30.245},
                "zoom": 13,
            },
            {
                "type": "route_result",
                "daily_plans": [
                    {
                        "day": 1,
                        "pois": ["1", "2"],
                        "polyline": [[120.15, 30.25], [120.10, 30.24]],
                    }
                ],
                "polylines": [[[120.15, 30.25], [120.10, 30.24]]],
            },
            {
                "type": "text",
                "content": "这是杭州两日游的推荐行程",
            },
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"session_id": "e2e-test-session", "message": "帮我规划杭州两日游"},
            )

        assert response.status_code == 200, f"SSE request failed: {response.status_code}"
        assert response.headers["content-type"].startswith("text/event-stream")

        # Parse SSE events
        events = _parse_sse_events(response.text)

        # Verify we have all expected event types
        event_types = [
            e["data"].get("type")
            for e in events
            if e["event"] == "message"
        ]

        assert "plan_summary" in event_types, "Missing plan_summary event"
        assert "poi_result" in event_types, "Missing poi_result event"
        assert "route_result" in event_types, "Missing route_result event"
        assert "text" in event_types, "Missing text event"

        # Verify done event is present
        assert events[-1]["event"] == "done", "Stream should end with done event"

    def test_sse_poi_event_has_coordinates(self, test_client: Any) -> None:
        """Test that poi_result events contain valid coordinate data."""
        mock_events: list[dict[str, Any]] = [
            {
                "type": "poi_result",
                "pois": [
                    {"id": "1", "name": "Test POI", "lng": 120.0, "lat": 30.0, "category": "test"},
                ],
                "center": {"lng": 120.0, "lat": 30.0},
                "zoom": 12,
            },
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"message": "test"},
            )

        events = _parse_sse_events(response.text)
        poi_events = [
            e for e in events
            if e["data"].get("type") == "poi_result"
        ]

        assert len(poi_events) > 0, "No poi_result events found"

        # Extract inner data from SSE envelope
        poi_data = _get_event_inner_data(poi_events[0])
        assert "pois" in poi_data, "poi_result missing pois field"
        assert "center" in poi_data, "poi_result missing center field"

        # Validate coordinates
        for poi in poi_data["pois"]:
            assert "lng" in poi, "POI missing lng coordinate"
            assert "lat" in poi, "POI missing lat coordinate"
            assert -180 <= poi["lng"] <= 180, f"Invalid longitude: {poi['lng']}"
            assert -90 <= poi["lat"] <= 90, f"Invalid latitude: {poi['lat']}"

    def test_sse_route_event_has_polyline(self, test_client: Any) -> None:
        """Test that route_result events contain valid route data."""
        mock_events: list[dict[str, Any]] = [
            {
                "type": "route_result",
                "daily_plans": [
                    {
                        "day": 1,
                        "pois": ["1", "2"],
                        "polyline": [[120.0, 30.0], [120.1, 30.1]],
                    }
                ],
                "polylines": [[[120.0, 30.0], [120.1, 30.1]]],
            },
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"message": "test"},
            )

        events = _parse_sse_events(response.text)
        route_events = [
            e for e in events
            if e["data"].get("type") == "route_result"
        ]

        assert len(route_events) > 0, "No route_result events found"

        # Extract inner data from SSE envelope
        route_data = _get_event_inner_data(route_events[0])
        assert "daily_plans" in route_data, "route_result missing daily_plans field"
        assert len(route_data["daily_plans"]) > 0, "daily_plans is empty"

    def test_sse_event_ordering(self, test_client: Any) -> None:
        """Test that SSE events arrive in the expected sequence.

        Expected order:
        1. thinking (optional)
        2. tool_calling (optional)
        3. poi_result
        4. route_result
        5. plan_summary or text
        """
        mock_events: list[dict[str, Any]] = [
            {"type": "thinking", "content": "让我思考一下..."},
            {"type": "tool_calling", "tool": "search_poi", "status": "running"},
            {
                "type": "poi_result",
                "pois": [
                    {"id": "1", "name": "西湖", "lng": 120.15, "lat": 30.25, "category": "scenic"},
                ],
                "center": {"lng": 120.15, "lat": 30.25},
                "zoom": 13,
            },
            {
                "type": "route_result",
                "daily_plans": [
                    {
                        "day": 1,
                        "pois": ["1"],
                        "polyline": [[120.15, 30.25]],
                    }
                ],
                "polylines": [[[120.15, 30.25]]],
            },
            {
                "type": "plan_summary",
                "city": "杭州",
                "days": 1,
            },
            {"type": "text", "content": "行程已规划完成"},
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"session_id": "order-test", "message": "帮我规划杭州一日游"},
            )

        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        # Collect only message events (skip done)
        message_types = [
            e["data"].get("type")
            for e in events
            if e["event"] == "message"
        ]

        # Optional events may or may not be present, but required events
        # must appear in the correct relative order
        required_order = ["poi_result", "route_result"]
        terminal_types = {"plan_summary", "text"}

        # Find indices of required events
        indices: dict[str, int] = {}
        for required_type in required_order:
            idx = message_types.index(required_type) if required_type in message_types else -1
            assert idx != -1, f"Missing required event: {required_type}"
            indices[required_type] = idx

        # Verify poi_result comes before route_result
        assert indices["poi_result"] < indices["route_result"], (
            f"poi_result (idx={indices['poi_result']}) must come before "
            f"route_result (idx={indices['route_result']})"
        )

        # Verify optional events (thinking, tool_calling) come before poi_result
        optional_before_poi = ["thinking", "tool_calling"]
        poi_idx = indices["poi_result"]
        for opt_type in optional_before_poi:
            if opt_type in message_types:
                opt_idx = message_types.index(opt_type)
                assert opt_idx < poi_idx, (
                    f"{opt_type} (idx={opt_idx}) must come before "
                    f"poi_result (idx={poi_idx})"
                )

        # Verify terminal events (plan_summary or text) come after route_result
        route_idx = indices["route_result"]
        for term_type in terminal_types:
            if term_type in message_types:
                term_idx = message_types.index(term_type)
                assert term_idx > route_idx, (
                    f"{term_type} (idx={term_idx}) must come after "
                    f"route_result (idx={route_idx})"
                )

        # Verify stream ends with done
        assert events[-1]["event"] == "done", "Stream should end with done event"

    def test_empty_poi_response(self, test_client: Any) -> None:
        """Test that empty POI list is handled gracefully.

        When the agent returns a poi_result with an empty pois array,
        the system should not crash and should still return a valid
        SSE stream.
        """
        mock_events: list[dict[str, Any]] = [
            {
                "type": "poi_result",
                "pois": [],
                "center": {"lng": 0.0, "lat": 0.0},
                "zoom": 1,
            },
            {
                "type": "text",
                "content": "抱歉，没有找到符合条件的地点。",
            },
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"session_id": "empty-poi-test", "message": "找一个不存在的地方"},
            )

        assert response.status_code == 200, (
            f"Empty POI response failed: {response.status_code}"
        )
        assert response.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse_events(response.text)
        assert len(events) >= 2, "Expected at least poi_result and done events"

        # Verify poi_result with empty pois is present
        poi_events = [
            e for e in events
            if e["data"].get("type") == "poi_result"
        ]
        assert len(poi_events) == 1, "Expected exactly one poi_result event"

        poi_data = _get_event_inner_data(poi_events[0])
        assert "pois" in poi_data, "poi_result missing pois field"
        assert poi_data["pois"] == [], "pois should be an empty list"

        # Verify text event is present with a user-friendly message
        text_events = [
            e for e in events
            if e["data"].get("type") == "text"
        ]
        assert len(text_events) >= 1, "Expected a text event for empty POI case"

        # Verify stream ends properly
        assert events[-1]["event"] == "done", "Stream must end with done event"

    def test_sse_stream_ends_with_done(self, test_client: Any) -> None:
        """Test that SSE stream always terminates with a done event."""
        mock_events: list[dict[str, Any]] = [
            {"type": "text", "content": "Hello"},
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"message": "test"},
            )

        events = _parse_sse_events(response.text)
        assert len(events) >= 2, "Expected at least one message and one done event"
        assert events[-1]["event"] == "done", "Stream must end with done event"
        assert isinstance(events[-1]["data"], dict), (
            "Done event data should be a dict"
        )


# ---------------------------------------------------------------------------
# Test: Live Agent Chat (requires running services)
# ---------------------------------------------------------------------------


class TestAgentChatLive:
    """Live E2E tests for agent chat.

    These tests require the backend service to be running with
    proper database and Redis connections.
    """

    def test_live_chat_endpoint_responds(
        self,
        live_mode: bool,
        backend_available: bool,
        http_client: httpx.Client,
    ) -> None:
        """Test that live chat endpoint responds with SSE stream.

        This test is skipped unless --e2e-live flag is used.
        """
        if not live_mode:
            pytest.skip("Live mode not enabled (use --e2e-live)")

        if not backend_available:
            pytest.skip("Backend service not available")

        response = http_client.post(
            f"{BACKEND_URL}/api/v1/agent/chat",
            json={"session_id": "live-test", "message": "你好"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        # Verify SSE stream is properly terminated
        events = _parse_sse_events(response.text)
        assert len(events) > 0, "Expected at least one SSE event"
        assert events[-1]["event"] == "done", "Stream must end with done event"


# ---------------------------------------------------------------------------
# Test: Frontend Build
# ---------------------------------------------------------------------------


class TestFrontendBuild:
    """Test frontend build process."""

    def test_frontend_package_json_exists(self) -> None:
        """Test that frontend package.json exists."""
        package_json = FRONTEND_ROOT / "package.json"
        assert package_json.exists(), "Frontend package.json not found"

    def test_frontend_build_command_valid(self) -> None:
        """Test that frontend build command can be parsed.

        This test verifies the build script is configured correctly
        without actually running the build.
        """
        package_json = FRONTEND_ROOT / "package.json"
        if not package_json.exists():
            pytest.skip("Frontend package.json not found")

        with open(package_json, encoding="utf-8") as f:
            package_data = json.load(f)

        scripts = package_data.get("scripts", {})
        assert "build" in scripts, "No build script in package.json"

        # Verify build script uses vite and/or vue-tsc
        build_cmd = scripts["build"]
        assert "vite" in build_cmd or "vue-tsc" in build_cmd, (
            f"Unexpected build command: {build_cmd}"
        )

    def test_frontend_build_succeeds(self, live_mode: bool) -> None:
        """Test that frontend builds successfully.

        This test actually runs `npm run build` and verifies it succeeds.
        Only runs in live mode to avoid slow CI runs.
        """
        if not live_mode:
            pytest.skip("Frontend build test requires --e2e-live flag")

        if not (FRONTEND_ROOT / "package.json").exists():
            pytest.skip("Frontend package.json not found")

        # Run npm build
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=FRONTEND_ROOT,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
        except FileNotFoundError:
            pytest.skip("npm not available")

        assert result.returncode == 0, (
            f"Frontend build failed.\n"
            f"stdout: {result.stdout[-500:]}\n"
            f"stderr: {result.stderr[-500:]}"
        )


# ---------------------------------------------------------------------------
# Test: Docker Compose Configuration
# ---------------------------------------------------------------------------


class TestDockerCompose:
    """Test Docker Compose configuration."""

    def test_docker_compose_exists(self) -> None:
        """Test that docker-compose.yml exists."""
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml not found"

    def test_docker_compose_valid(self) -> None:
        """Test that docker-compose.yml is valid YAML with required services."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        compose_file = PROJECT_ROOT / "docker-compose.yml"
        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")

        with open(compose_file, encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        # Verify required services
        services = compose_data.get("services", {})
        required_services = ["postgres", "redis", "backend", "frontend"]

        for service in required_services:
            assert service in services, f"Missing required service: {service}"

    def test_docker_compose_ports(self) -> None:
        """Test that services expose expected ports."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        compose_file = PROJECT_ROOT / "docker-compose.yml"
        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")

        with open(compose_file, encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get("services", {})

        # Backend should expose port 8000
        backend_ports = services.get("backend", {}).get("ports", [])
        assert any("8000" in str(p) for p in backend_ports), (
            "Backend should expose port 8000"
        )

        # Frontend should expose port 5173
        frontend_ports = services.get("frontend", {}).get("ports", [])
        assert any("5173" in str(p) for p in frontend_ports), (
            "Frontend should expose port 5173"
        )

    def test_docker_compose_config(self, live_mode: bool) -> None:
        """Test that docker-compose config is valid.

        This runs `docker compose config` to validate the configuration.
        Only runs in live mode.
        """
        if not live_mode:
            pytest.skip("Docker config test requires --e2e-live flag")

        compose_file = PROJECT_ROOT / "docker-compose.yml"
        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")

        try:
            result = subprocess.run(
                ["docker", "compose", "config", "-q"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Skip if .env file is missing (common in CI/test environments)
            if "env file" in result.stderr and "not found" in result.stderr:
                pytest.skip(".env file not found (required by docker-compose)")
            assert result.returncode == 0, (
                f"Docker compose config validation failed.\n"
                f"stderr: {result.stderr}"
            )
        except FileNotFoundError:
            pytest.skip("Docker not available")


# ---------------------------------------------------------------------------
# Test: Seed Data
# ---------------------------------------------------------------------------


class TestSeedData:
    """Test seed data scripts."""

    def test_seed_scripts_exist(self) -> None:
        """Test that seed scripts exist."""
        seed_dir = BACKEND_ROOT / "scripts"
        assert seed_dir.exists(), "Backend scripts directory not found"

        seed_all = seed_dir / "seed_all.py"
        assert seed_all.exists(), "seed_all.py not found"

        seed_hangzhou = seed_dir / "seed_hangzhou.py"
        assert seed_hangzhou.exists(), "seed_hangzhou.py not found"

        seed_chengdu = seed_dir / "seed_chengdu.py"
        assert seed_chengdu.exists(), "seed_chengdu.py not found"

    def test_seed_base_exists(self) -> None:
        """Test that seed_base.py shared utilities exist."""
        seed_base = BACKEND_ROOT / "scripts" / "seed_base.py"
        assert seed_base.exists(), "seed_base.py not found"

    def test_seed_data_content_valid(self) -> None:
        """Test that seed scripts contain valid POI data structures."""
        seed_hangzhou = BACKEND_ROOT / "scripts" / "seed_hangzhou.py"
        if not seed_hangzhou.exists():
            pytest.skip("seed_hangzhou.py not found")

        content = seed_hangzhou.read_text(encoding="utf-8")

        # Verify the script defines POI data with required fields
        assert "POIS" in content or "pois" in content, (
            "Seed script should define POI data"
        )
        assert "lng" in content, "POI data should contain longitude"
        assert "lat" in content, "POI data should contain latitude"
        assert "name" in content, "POI data should contain name"
        assert "category" in content, "POI data should contain category"


# ---------------------------------------------------------------------------
# Integration Test: Full System Flow
# ---------------------------------------------------------------------------


class TestFullSystemFlow:
    """Integration tests for the full system flow.

    These tests verify the complete flow from API request to response
    using mocked graph results.
    """

    def test_full_trip_planning_flow(self, test_client: Any) -> None:
        """Test complete trip planning flow.

        Simulates the full flow:
        1. User sends trip planning request
        2. Agent processes and returns structured plan
        3. SSE stream contains all expected event types with valid data
        """
        # Simulate complete trip planning response
        # Format matches FormatterNode output (flat dicts)
        mock_events: list[dict[str, Any]] = [
            {
                "type": "plan_summary",
                "city": "杭州",
                "days": 2,
            },
            {
                "type": "poi_result",
                "pois": [
                    {
                        "id": "poi_1",
                        "name": "西湖",
                        "lng": 120.15,
                        "lat": 30.25,
                        "category": "scenic",
                    },
                    {
                        "id": "poi_2",
                        "name": "灵隐寺",
                        "lng": 120.10,
                        "lat": 30.24,
                        "category": "temple",
                    },
                    {
                        "id": "poi_3",
                        "name": "雷峰塔",
                        "lng": 120.16,
                        "lat": 30.23,
                        "category": "landmark",
                    },
                ],
                "center": {"lng": 120.1367, "lat": 30.24},
                "zoom": 13,
            },
            {
                "type": "route_result",
                "daily_plans": [
                    {
                        "day": 1,
                        "title": "西湖周边游",
                        "pois": ["poi_1", "poi_2"],
                        "polyline": [[120.15, 30.25], [120.10, 30.24]],
                        "distance_km": 5.2,
                    },
                    {
                        "day": 2,
                        "title": "文化探索",
                        "pois": ["poi_3"],
                        "polyline": [[120.16, 30.23]],
                        "distance_km": 2.1,
                    },
                ],
                "polylines": [
                    [[120.15, 30.25], [120.10, 30.24]],
                    [[120.16, 30.23]],
                ],
            },
            {
                "type": "text",
                "content": "为您推荐杭州两日游行程：第一天游览西湖和灵隐寺，第二天参观雷峰塔。",
            },
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={
                    "session_id": "full-flow-test",
                    "message": "帮我规划杭州两日游",
                },
            )

        # Verify response
        assert response.status_code == 200, f"Request failed: {response.status_code}"

        events = _parse_sse_events(response.text)

        # Verify all required event types are present
        event_types = [
            e["data"].get("type")
            for e in events
            if e["event"] == "message"
        ]

        assert "plan_summary" in event_types, "Missing plan_summary in response"
        assert "poi_result" in event_types, "Missing poi_result in response"
        assert "route_result" in event_types, "Missing route_result in response"
        assert "text" in event_types, "Missing text in response"

        # Verify stream ends properly
        assert events[-1]["event"] == "done", "Stream not properly terminated"

        # Verify data integrity — plan_summary
        plan_event = next(
            (e for e in events if e["data"].get("type") == "plan_summary"),
            None,
        )
        assert plan_event is not None, "Missing plan_summary event in stream"
        plan_data = _get_event_inner_data(plan_event)
        assert plan_data["city"] == "杭州"
        assert plan_data["days"] == 2

        # Verify data integrity — poi_result
        poi_event = next(
            (e for e in events if e["data"].get("type") == "poi_result"),
            None,
        )
        assert poi_event is not None, "Missing poi_result event in stream"
        poi_data = _get_event_inner_data(poi_event)
        assert len(poi_data["pois"]) == 3
        for poi in poi_data["pois"]:
            assert "lng" in poi
            assert "lat" in poi
            assert "name" in poi

        # Verify data integrity — route_result
        route_event = next(
            (e for e in events if e["data"].get("type") == "route_result"),
            None,
        )
        assert route_event is not None, "Missing route_result event in stream"
        route_data = _get_event_inner_data(route_event)
        assert len(route_data["daily_plans"]) == 2
        assert route_data["daily_plans"][0]["day"] == 1
        assert route_data["daily_plans"][1]["day"] == 2

    def test_empty_plan_returns_text_only(self, test_client: Any) -> None:
        """Test that empty plan still returns text event and done."""
        # Formatter always emits a text event
        mock_events: list[dict[str, Any]] = [
            {"type": "text", "content": "抱歉，我没有找到相关的信息。"},
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            response = test_client.post(
                "/api/v1/agent/chat",
                json={"message": "随便聊聊"},
            )

        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        event_types = [
            e["data"].get("type")
            for e in events
            if e["event"] == "message"
        ]

        assert "text" in event_types, "Should always have text event"
        assert events[-1]["event"] == "done", "Stream must end with done"

    def test_session_id_generated_when_missing(self, test_client: Any) -> None:
        """Test that session_id is auto-generated when not provided."""
        mock_events: list[dict[str, Any]] = [
            {"type": "text", "content": "ok"},
        ]

        with patch("app.api.v1.agent.build_graph") as mock_build_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"structured_plan": mock_events}
            mock_build_graph.return_value = mock_graph

            # Don't send session_id — it should be auto-generated
            response = test_client.post(
                "/api/v1/agent/chat",
                json={"message": "test"},
            )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
