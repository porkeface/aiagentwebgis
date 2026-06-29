from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings


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
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(v1_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()
