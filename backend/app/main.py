"""FastAPI application factory with middleware and router wiring."""

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import settings


# ---------------------------------------------------------------------------
# Lightweight in-memory rate limiter
# ---------------------------------------------------------------------------
# A per-client token-bucket / sliding-window counter. Sufficient for a single
# process — production multi-worker deployments should swap this for Redis
# (the interface is identical: `is_allowed(client_id)` returns False when
# the client has exceeded their budget in the current window).
# ---------------------------------------------------------------------------

class _SlidingWindowLimiter:
    """Per-key sliding-window rate limiter.

    Records each call's timestamp in a deque per key, and prunes entries
    older than ``window_seconds`` on every check. ``is_allowed`` returns
    False once a key has more than ``max_calls`` timestamps in the window.
    """

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            bucket = self._calls[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_calls:
                return False
            bucket.append(now)
            return True


# Per-route limiters. Agent chat is the most expensive (LLM + Amap calls)
# so it gets the tightest budget.
_AGENT_CHAT_LIMITER = _SlidingWindowLimiter(max_calls=20, window_seconds=60.0)
_AUTH_LIMITER = _SlidingWindowLimiter(max_calls=10, window_seconds=60.0)


def _client_key(request: Request) -> str:
    """Best-effort client identifier for rate limiting.

    Prefers the authenticated user (so a logged-in user keeps their budget
    when sharing a NAT with anonymous traffic), then the X-Forwarded-For
    chain, then falls back to the raw client host.
    """
    user = getattr(request.state, "user_id", None)
    if user is not None:
        return f"user:{user}"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Travel Planner API",
        description=(
            "AI-powered travel planning system backend.\n\n"
            "## Features\n\n"
            "- **Agent Chat**: Multi-turn conversation with AI to plan trips (SSE streaming)\n"
            "- **POI Search**: Search points of interest with spatial filters, categories, and keywords\n"
            "- **Trip CRUD**: Create, read, update, and delete trips with daily plans\n"
            "- **Auth**: JWT-based authentication (register/login)\n\n"
            "## Workflow\n\n"
            "1. Register/login via `/api/v1/auth`\n"
            "2. Chat with AI agent via `/api/v1/agent/chat` (SSE)\n"
            "3. Agent auto-creates trips with POIs and routes\n"
            "4. View trip details via `/api/v1/trips/{id}`\n\n"
            "## SSE Event Types\n\n"
            "| Event Type | Description |\n"
            "|---|---|\n"
            "| `thinking` | AI is reasoning |\n"
            "| `tool_calling` | AI calling a tool |\n"
            "| `poi_result` | POI search results |\n"
            "| `route_result` | Route visualization data |\n"
            "| `plan_summary` | Trip plan summary |\n"
            "| `text` | Text response |\n"
            "| `error` | Error message |\n"
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------------
    # Rate-limit middleware (pure ASGI — does NOT buffer streaming responses)
    # ---------------------------------------------------------------------
    # Starlette's BaseHTTPMiddleware wraps the response body, which breaks SSE
    # streaming by buffering the entire body.  We use a raw ASGI middleware to
    # rate-limit without touching the stream payload.
    from starlette.types import ASGIApp, Receive, Scope, Send, Message

    class RateLimitMiddleware:
        """Per-path sliding-window rate limiter as a raw ASGI middleware.

        This intentionally does NOT use ``BaseHTTPMiddleware``, which buffers
        the response body and breaks SSE streaming.
        """

        def __init__(self, app: ASGIApp) -> None:
            self._app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] != "http":
                await self._app(scope, receive, send)
                return

            path = scope["path"]
            if path.startswith("/api/v1/agent/"):
                limiter = _AGENT_CHAT_LIMITER
            elif path.startswith("/api/v1/auth/"):
                limiter = _AUTH_LIMITER
            else:
                await self._app(scope, receive, send)
                return

            # Build a request to resolve the client key
            request = Request(scope, receive)
            if not await limiter.is_allowed(_client_key(request)):
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, slow down."},
                )
                await response(scope, receive, send)
                return

            await self._app(scope, receive, send)

    app.add_middleware(RateLimitMiddleware)

    # Include routers
    app.include_router(v1_router)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        """Release process-wide resources on shutdown."""
        try:
            from agent.tools import close_amap
            await close_amap()
        except Exception:
            logger.exception("Failed to close AmapService on shutdown")
        try:
            from app.services.redis_client import close_redis
            await close_redis()
        except Exception:
            logger.exception("Failed to close Redis on shutdown")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()
