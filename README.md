# AI Travel Planner 🗺️

AI-powered travel planning system. Plan trips through natural conversation with an AI assistant, get personalized POI recommendations, and visualize your itinerary on an interactive map.

## ✨ Features

- **AI Conversation Planning**: Chat with AI to plan multi-day trips with natural language
- **Smart POI Search**: Spatial filtering, multi-factor scoring, and diversity-aware recommendations
- **Interactive Map**: Leaflet-based map with real-time POI markers and route visualization
- **Trip Management**: Create, view, edit, and delete trips with daily timeline
- **Dialog-Map Linkage**: Click POI in chat → zoom on map; click map marker → highlight in chat
- **Multi-turn Context**: AI remembers conversation history for progressive refinement
- **JWT Authentication**: Secure user registration and login

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + TypeScript + Vite + Element Plus + Leaflet |
| Backend | FastAPI + SQLAlchemy (async) + LangGraph |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Cache | Redis 7 |
| AI/LLM | DashScope (Qwen) |
| Map | Amap (Gaode) API |
| Containerization | Docker + Docker Compose |

## 📁 Project Structure

```text
aiagentwebgis/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API routers (auth, poi, trip, agent)
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── main.py          # FastAPI app factory
│   │   ├── config.py        # Settings (env-based)
│   │   └── database.py      # DB session management
│   ├── agent/               # LangGraph agent graph
│   ├── tests/               # pytest tests
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # API client modules
│   │   ├── components/      # Vue components (map, chat, trip)
│   │   ├── stores/          # Pinia stores
│   │   ├── views/           # Page views
│   │   └── types/           # TypeScript types
│   └── Dockerfile
├── docs/
│   ├── user-manual.md       # User guide
│   └── demo-script.md       # Demo test cases
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- [Amap API Key](https://lbs.amap.com/)
- [DashScope API Key](https://dashscope.console.aliyun.com/)

### 1. Clone and Configure

```bash
git clone <repo-url>
cd aiagentwebgis
cp .env.example .env
```

Edit `.env` with your keys:

```env
DB_PASSWORD=your_secure_password
AMAP_API_KEY=your_amap_key
DASHSCOPE_API_KEY=your_dashscope_key
JWT_SECRET_KEY=your_random_jwt_secret
```

### 2. Start Services

```bash
docker compose up -d                # Postgres + Redis
```

| Service | Port | How to start |
|---------|------|--------------|
| PostgreSQL | 5432 | `docker compose up -d postgres` |
| Redis | 6379 | `docker compose up -d redis` |
| Backend | 8000 | `cd backend && uv run uvicorn app.main:app --reload` |
| Frontend | 5173 | `cd frontend && npm run dev` |

The backend and frontend run on the host (not in Docker) so you get hot-reload
and direct access to logs. See the docker-compose.yml comment for the rationale.

### 3. Access

- **Frontend**: http://localhost:5173
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: `curl http://localhost:8000/health`

### 4. Stop

```bash
docker compose down          # Stop infra services
docker compose down -v       # Stop and remove data
# Ctrl-C to stop backend/frontend
```

## 📖 API Overview

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get JWT token |

### Agent Chat (SSE)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agent/chat` | Chat with AI agent (Server-Sent Events) |

### POI Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/poi/search` | Search POIs with filters |

### Trip Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/trips` | Create trip |
| GET | `/api/v1/trips` | List user trips |
| GET | `/api/v1/trips/{id}` | Get trip detail |
| PUT | `/api/v1/trips/{id}` | Update trip |
| DELETE | `/api/v1/trips/{id}` | Delete trip |

All trip endpoints require JWT authentication (`Authorization: Bearer <token>`).

## 🧪 Demo

See [docs/demo-script.md](docs/demo-script.md) for 5 test scenarios:

1. Basic trip planning ("帮我规划杭州3日游")
2. POI search ("成都附近有什么好吃的")
3. Multi-turn conversation (refine preferences)
4. Trip detail view
5. Error handling (network failure)

## 📚 Documentation

- [User Manual](docs/user-manual.md) — Complete user guide
- [Demo Script](docs/demo-script.md) — Test scenarios for demo
- [Design Document](docs/superpowers/specs/2026-06-29-ai-travel-planner-design.md) — System design

## 🔒 Security

- JWT-based authentication with configurable expiration
- Password hashing (bcrypt)
- CORS restricted to frontend origin
- No hardcoded secrets (all via environment variables)
- Input validation on all API endpoints

## 📄 License

MIT
