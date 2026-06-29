### Task 1.1: Project Scaffolding

**Files:**
- Create: `docker-compose.yml`, `.env.example`, `backend/Dockerfile`, `backend/requirements.txt`
- Create: `backend/app/main.py`, `backend/app/config.py`
- Create: `frontend/` (Vite scaffold with vue-ts template)
- Test: `backend/tests/conftest.py`

**Consumes:** Nothing (first task)
**Produces:** FastAPI /health endpoint, Vue3 dev server, Docker Compose with PostGIS + Redis

**Steps:**

1. Create `docker-compose.yml` with 4 services: postgres (postgis/postgis:16-3.4), redis (7-alpine), backend (FastAPI), frontend (Vite)
2. Create `.env.example` with all env vars (DB_PASSWORD, DATABASE_URL, REDIS_URL, DASHSCOPE_API_KEY, LLM_PROVIDER, AMAP_API_KEY, JWT_SECRET_KEY)
3. Create `backend/requirements.txt` with all dependencies (fastapi, sqlalchemy, geoalchemy2, langgraph, dashscope, httpx, scikit-learn, etc.)
4. Create `backend/app/config.py` using pydantic-settings BaseSettings
5. Create `backend/app/main.py` with CORS middleware and /health endpoint
6. Create `backend/Dockerfile` (python:3.11-slim, install deps, copy app)
7. Scaffold frontend: `npm create vite@latest . -- --template vue-ts`, install leaflet, element-plus, pinia
8. Create `frontend/src/main.ts` (Pinia + ElementPlus + Leaflet CSS)
9. Create `backend/tests/conftest.py` with httpx AsyncClient fixture
10. Verify: `curl http://localhost:8000/health` returns `{"status":"ok"}`
11. Commit: `feat: project scaffolding - Docker Compose, FastAPI, Vue3+Vite`

---