---
change: ai-travel-planner
design-doc: docs/superpowers/specs/2026-06-29-ai-travel-planner-design.md
base-ref: d94535f
archived-with: 2026-06-29-ai-travel-planner
---

# AI Travel Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an AI Agent-based travel route planning and scenic spot recommendation system with WebGIS visualization.

**Architecture:** Four-layer architecture (Frontend Vue3+Leaflet -> Backend FastAPI -> Agent LangGraph StateGraph -> Data PostgreSQL/PostGIS). Core brain is Planner Agent using ReAct pattern with shared State whiteboard. SSE streaming for real-time dialog-map linkage.

**Tech Stack:** Vue 3 + Vite + TypeScript, Leaflet + Amap tiles, Element Plus, Pinia, FastAPI, SQLAlchemy 2.0 + GeoAlchemy2, LangGraph, Tongyi Qwen (DashScope), PostgreSQL + PostGIS, Redis, Docker Compose

## Global Constraints

- Python 3.11+, Node.js 18+
- All API responses use envelope: `{"success": bool, "data": any, "error": str|null}`
- All async endpoints use `async/await`
- SSE format: `event: message` then `data: {"type": "<msg_type>", "content": <any>}`
- PostGIS SRID: 4326 (WGS84)
- LLM temperature: 0.3
- Docker Compose for all services
- No hardcoded secrets, env vars only

archived-with: 2026-06-29-ai-travel-planner
---

## File Structure

```
aiagentwebgis/
+-- frontend/src/
|   +-- api/          (agent.ts, poi.ts, trip.ts, auth.ts)
|   +-- components/
|   |   +-- map/      (MapView.vue, PoiMarker.vue, RouteLayer.vue)
|   |   +-- chat/     (ChatPanel.vue, MessageBubble.vue)
|   |   +-- trip/     (TripTimeline.vue, DayCard.vue)
|   +-- stores/       (chat.ts, map.ts, trip.ts)
|   +-- views/        (HomeView.vue, TripDetailView.vue)
|   +-- types/        (index.ts)
+-- backend/
|   +-- app/
|   |   +-- api/v1/   (router.py, agent.py, poi.py, trip.py, auth.py)
|   |   +-- models/   (poi.py, trip.py, user.py, chat.py)
|   |   +-- schemas/  (poi.py, trip.py, agent.py, auth.py)
|   |   +-- services/ (poi_service.py, trip_service.py, auth_service.py, amap_service.py)
|   +-- agent/
|   |   +-- graph.py, state.py, checkpointer.py
|   |   +-- nodes/    (router.py, planner.py, formatter.py)
|   |   +-- tools/    (poi_search.py, geocoding.py, route_planning.py, spatial_analysis.py, weather.py)
|   |   +-- llm/      (base.py, tongyi.py, openai_adapter.py, ollama.py, factory.py)
|   +-- recommendation/ (spatial_filter.py, scoring.py, mmr.py, clustering.py, tsp.py, pipeline.py)
|   +-- tests/
+-- data/seed/        (seed_hangzhou.py, seed_chengdu.py)
+-- docker-compose.yml
+-- .env.example
```

archived-with: 2026-06-29-ai-travel-planner
---

## Task Index

| # | Task | Phase | Key Files |
|---|------|-------|-----------|
| 1.1 | Project Scaffolding | Foundation | docker-compose.yml, backend/Dockerfile, frontend/ |
| 1.2 | Database Models | Foundation | backend/app/models/, database.py |
| 1.3 | Amap API Service | Foundation | backend/app/services/amap_service.py |
| 1.4 | LLM Adapter Layer | Foundation | backend/agent/llm/ |
| 2.1 | LangGraph + Router | Agent Core | agent/state.py, graph.py, nodes/router.py |
| 2.2 | Agent Tool Chain | Agent Core | agent/tools/ (6 tools) |
| 2.3 | Planner Agent | Agent Core | agent/nodes/planner.py |
| 2.4 | Formatter Node | Agent Core | agent/nodes/formatter.py |
| 3.1 | Spatial Filter | Spatial | recommendation/spatial_filter.py |
| 3.2 | Multi-Factor Scoring | Spatial | recommendation/scoring.py |
| 3.3 | MMR Diversity Rerank | Spatial | recommendation/mmr.py |
| 3.4 | DBSCAN Clustering | Spatial | recommendation/clustering.py |
| 3.5 | TSP Optimization | Spatial | recommendation/tsp.py |
| 3.6 | Recommendation Pipeline | Spatial | recommendation/pipeline.py |
| 4.1 | Pydantic Schemas | API | backend/app/schemas/ |
| 4.2 | POI Service + API | API | services/poi_service.py, api/v1/poi.py |
| 4.3 | Agent Chat SSE | API | api/v1/agent.py |
| 4.4 | Trip CRUD | API | services/trip_service.py, api/v1/trip.py |
| 4.5 | JWT Auth | API | services/auth_service.py, api/v1/auth.py |
| 5.1 | Types + API Layer | Frontend | frontend/src/types/, api/ |
| 5.2 | Pinia Stores | Frontend | frontend/src/stores/ |
| 5.3 | MapView | Frontend | components/map/MapView.vue |
| 5.4 | Chat Panel | Frontend | components/chat/ChatPanel.vue |
| 5.5 | Dialog-Map Linkage | Frontend | stores/chat.ts + map.ts integration |
| 5.6 | Route Visualization | Frontend | components/map/RouteLayer.vue |
| 5.7 | Trip Detail | Frontend | components/trip/, views/TripDetailView.vue |
| 5.8 | HomeView Assembly | Frontend | views/HomeView.vue |
| 6.1 | Seed Data | Integration | data/seed/ |
| 6.2 | E2E Smoke Test | Integration | end-to-end validation |
| 6.3 | Error Handling | Integration | fallback + graceful degradation |
| 6.4 | UI Polish | Integration | styling, responsive, animations |
| 7.1 | Backend Tests | Testing | backend/tests/ |
| 7.2 | Frontend E2E | Testing | frontend/tests/ |
| 7.3 | Docs + Demo | Testing | docs/ |

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 1: Foundation

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

archived-with: 2026-06-29-ai-travel-planner
---

### Task 1.2: Database Models

**Files:**
- Create: `backend/app/database.py`, `backend/app/models/__init__.py`
- Create: `backend/app/models/poi.py` (POI with PostGIS GEOMETRY POINT)
- Create: `backend/app/models/trip.py` (Trip, TripDay, TripDayPOI)
- Create: `backend/app/models/user.py` (User)
- Create: `backend/app/models/chat.py` (ChatSession)
- Test: `backend/tests/test_models.py`

**Consumes:** config.py (DATABASE_URL)
**Produces:** 6 ORM models with spatial types, Base DeclarativeBase class

**Steps:**

1. Create `database.py` with async engine + session factory
2. Create POI model: id, name, category, city, location (Geometry POINT 4326), rating, tags (ARRAY), description, opening_hours, avg_visit_duration, review_count, extra_data, created_at. Include to_dict() method.
3. Create Trip/TripDay/TripDayPOI models with relationships and cascading deletes
4. Create User model: id, username (unique), hashed_password, nickname
5. Create ChatSession model: id, user_id, title, messages_json, agent_state_json
6. Create `models/__init__.py` exporting all models
7. Write tests verifying all model fields and relationships
8. Run: `pytest tests/test_models.py -v` -- all pass
9. Commit: `feat: database models - POI(PostGIS), Trip, User, ChatSession`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 1.3: Amap API Service

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/amap_service.py`
- Test: `backend/tests/test_amap_service.py`

**Consumes:** config.py (AMAP_API_KEY)
**Produces:** AmapService class with search_pois(), geocode(), reverse_geocode(), plan_route()

**Steps:**

1. Write tests first (mock httpx responses):
   - test_search_pois_returns_list: mock response with 1 POI, verify parsing
   - test_geocode_returns_coordinates: mock geocode response, verify (lng, lat) tuple
   - test_plan_route_returns_polyline: mock route response, verify distance_km, duration_min, polyline
   - test_search_pois_handles_empty: mock empty response, verify returns []

2. Create AmapService:
   - `__init__(api_key)`: store key
   - `_request(endpoint, params)`: internal httpx GET with key injection
   - `search_pois(city, keyword?, category?, limit=20)`: GET place/text, parse pois to list of dicts with lng/lat
   - `geocode(address)`: GET geocode/geo, return (lng, lat)
   - `reverse_geocode(lng, lat)`: GET geocode/regeo, return {address, city}
   - `plan_route(origin, destination, mode="walking")`: GET direction/{mode}, return {distance_km, duration_min, polyline}

3. Run: `pytest tests/test_amap_service.py -v` -- all 4 pass
4. Commit: `feat: Amap API service - POI search, geocoding, route planning`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 1.4: LLM Adapter Layer

**Files:**
- Create: `backend/agent/__init__.py`, `backend/agent/llm/__init__.py`
- Create: `backend/agent/llm/base.py` (BaseLLMAdapter ABC, LLMResponse, ToolCall, LLMChunk dataclasses)
- Create: `backend/agent/llm/tongyi.py` (TongyiAdapter with tool_call + prompt fallback)
- Create: `backend/agent/llm/openai_adapter.py` (OpenAIAdapter)
- Create: `backend/agent/llm/ollama.py` (OllamaAdapter)
- Create: `backend/agent/llm/factory.py` (get_llm_adapter() factory)
- Test: `backend/tests/test_agent/test_llm_adapter.py`

**Consumes:** config.py (LLM_PROVIDER, DASHSCOPE_API_KEY)
**Produces:** BaseLLMAdapter ABC, 3 adapter implementations, factory function

**Steps:**

1. Define dataclasses in base.py:
   - ToolCall(id, name, arguments)
   - LLMResponse(content, tool_calls, usage)
   - LLMChunk(content, tool_call_delta, is_done)
   - BaseLLMAdapter ABC: chat(messages, tools?) -> LLMResponse, stream(messages, tools?) -> AsyncIterator[LLMChunk]

2. TongyiAdapter:
   - Uses langchain_community ChatTongyi
   - _tool_call_chat: normal path with tools param
   - _prompt_based_fallback: injects tool descriptions into system prompt, parses JSON from response text
   - _format_tools_as_prompt: converts tool schemas to text descriptions
   - _parse_tool_calls_from_text: regex extract JSON with "tool" and "args" fields

3. OpenAIAdapter: uses langchain_openai ChatOpenAI, standard tool calling
4. OllamaAdapter: uses langchain_community ChatOllama, for local dev
5. factory.py: get_llm_adapter() reads LLM_PROVIDER env, returns correct adapter

6. Write tests:
   - test_llm_response_structure
   - test_tool_call_structure
   - test_tongyi_parse_tool_calls_from_json_text
   - test_tongyi_parse_tool_calls_handles_no_json
   - test_tongyi_format_tools_as_prompt
   - test_factory_returns_tongyi

7. Run: `pytest tests/test_agent/test_llm_adapter.py -v` -- all 6 pass
8. Commit: `feat: LLM adapter layer - Tongyi with fallback, OpenAI, Ollama`

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 2: Agent Core

### Task 2.1: LangGraph StateGraph + Router

**Files:**
- Create: `backend/agent/state.py` (AgentState TypedDict)
- Create: `backend/agent/graph.py` (build_graph() -> compiled StateGraph)
- Create: `backend/agent/nodes/__init__.py`, `backend/agent/nodes/router.py`
- Test: `backend/tests/test_agent/test_router.py`

**Consumes:** agent/llm (for future LLM-based intent classification)
**Produces:** AgentState type, compiled LangGraph with router->planner/formatter routing

**Steps:**

1. Define AgentState TypedDict with all fields: messages, session_id, intent, city, days, preferences, companion_types, budget_level, candidate_pois, selected_pois, daily_plans, route_polylines, recommendation_weights, response_text, structured_plan

2. Create RouterNode:
   - Keyword-based intent classification (MVP): TRIP_KEYWORDS, POI_KEYWORDS, GREETING_KEYWORDS
   - _classify_intent(text) -> "trip_planning" | "poi_recommendation" | "general"
   - route(state) -> updated state with intent set

3. Create build_graph():
   - StateGraph(AgentState) with 3 nodes: router, planner, formatter
   - START -> router -> conditional_edges(trip_planning/poi_recommendation -> planner, general -> formatter)
   - planner -> formatter -> END
   - planner/formatter are placeholders (Tasks 2.3, 2.4)

4. Write tests:
   - test_router_classifies_trip_planning: "帮我规划杭州两日游" -> trip_planning
   - test_router_classifies_poi_recommendation: "杭州有什么好吃的" -> poi_recommendation
   - test_router_classifies_general: "你好" -> general
   - test_agent_state_has_required_fields

5. Run: `pytest tests/test_agent/test_router.py -v` -- all 4 pass
6. Commit: `feat: LangGraph StateGraph with Router node and conditional routing`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 2.2: Agent Tool Chain

**Files:**
- Create: `backend/agent/tools/__init__.py`
- Create: `backend/agent/tools/poi_search.py` (search_pois_tool, search_nearby_tool)
- Create: `backend/agent/tools/geocoding.py` (geocode_tool, reverse_geocode_tool)
- Create: `backend/agent/tools/route_planning.py` (plan_route_tool)
- Create: `backend/agent/tools/spatial_analysis.py` (score_pois_tool)
- Create: `backend/agent/tools/weather.py` (get_weather_tool)
- Test: `backend/tests/test_agent/test_tools.py`

**Consumes:** services/amap_service.py
**Produces:** 6 tool functions + ALL_TOOLS list for LangGraph registration

**Steps:**

1. poi_search.py: search_pois_tool wraps amap.search_pois; search_nearby_tool uses amap place/around
2. geocoding.py: geocode_tool wraps amap.geocode; reverse_geocode_tool wraps amap.reverse_geocode
3. route_planning.py: plan_route_tool wraps amap.plan_route
4. spatial_analysis.py: score_pois_tool implements multi-factor scoring (preference Jaccard + inverse distance + rating + time + popularity)
5. weather.py: get_weather_tool returns placeholder data (MVP)
6. get_amap() singleton factory pattern
7. ALL_TOOLS list in __init__.py

8. Write tests (mock amap service):
   - test_search_pois_tool: mock returns 1 POI, verify result
   - test_geocode_tool: mock returns coordinates
   - test_plan_route_tool: mock returns route
   - test_score_pois_tool: verify scoring calculation
   - test_get_weather_tool: verify placeholder structure

9. Run: `pytest tests/test_agent/test_tools.py -v` -- all 5 pass
10. Commit: `feat: Agent tool chain - 6 tools for POI search, routing, scoring, weather`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 2.3: Planner Agent (ReAct)

**Files:**
- Create: `backend/agent/nodes/planner.py`
- Modify: `backend/agent/graph.py` (replace placeholder with real PlannerNode)
- Test: `backend/tests/test_agent/test_planner.py`

**Consumes:** agent/llm (BaseLLMAdapter), agent/tools, agent/state
**Produces:** PlannerNode that extracts params, calls LLM, updates state

**Steps:**

1. Define SYSTEM_PROMPT for travel planning assistant
2. Define regex patterns for city/days extraction from text
3. PlannerNode class:
   - __init__(llm_adapter)
   - plan(state) -> state: extract params, ensure weights, build messages, call LLM, set response_text
   - _extract_params(state): regex extract city and days from last user message
   - _ensure_weights(state): set default weights based on companion_types

4. Update graph.py to use PlannerNode instead of placeholder
5. Write tests:
   - test_planner_produces_response_text: mock LLM, verify response_text is set
   - test_planner_extracts_city_from_message: verify city extraction
   - test_planner_sets_default_weights: verify weights are populated

6. Run: `pytest tests/test_agent/test_planner.py -v` -- all 3 pass
7. Commit: `feat: Planner Agent node with ReAct pattern and parameter extraction`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 2.4: Formatter Node

**Files:**
- Create: `backend/agent/nodes/formatter.py`
- Modify: `backend/agent/graph.py` (replace placeholder with real FormatterNode)
- Test: `backend/tests/test_agent/test_formatter.py`

**Consumes:** AgentState with planning results
**Produces:** List of SSE event dicts

**Steps:**

1. FormatterNode class with format(state) -> list[dict]:
   - If candidate_pois: emit poi_result event (pois + center + zoom)
   - If daily_plans: emit route_result event (daily_plans + polylines)
   - If city + days: emit plan_summary event
   - Always emit text event with response_text

2. _calc_center(pois): average lng/lat of POIs

3. Update graph.py to use FormatterNode, store events in state["structured_plan"]

4. Write tests:
   - test_formatter_produces_sse_events: verify event list has text
   - test_formatter_includes_poi_result: verify poi_result with correct POI count
   - test_formatter_includes_route_result: verify route_result
   - test_formatter_general_intent_text_only: no poi_result for general intent

5. Run: `pytest tests/test_agent/test_formatter.py -v` -- all 4 pass
6. Commit: `feat: Formatter node - SSE event packaging from AgentState`

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 3: Spatial Recommendation Engine

### Task 3.1: Spatial Filter

**Files:**
- Create: `backend/recommendation/__init__.py`, `backend/recommendation/spatial_filter.py`
- Test: `backend/tests/test_recommendation/test_spatial_filter.py`

**Consumes:** database.py, models/poi.py (POI model)
**Produces:** spatial_filter_pois(city, center_lng, center_lat, radius_km) -> list[POI]

**Steps:**

1. Write spatial filter using SQLAlchemy + GeoAlchemy2:
   - ST_DWithin(location, func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326), radius_degrees)
   - Fallback: if local results < min_count, return flag for Amap API supplement
   - radius_degrees = radius_km / 111.0 (approximate)

2. Write tests:
   - test_spatial_filter_returns_pois_within_radius
   - test_spatial_filter_excludes_pois_outside_radius
   - test_spatial_filter_empty_city_returns_empty

3. Run tests, commit: `feat: spatial filter - PostGIS ST_DWithin query`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 3.2: Multi-Factor Scoring

**Files:**
- Create: `backend/recommendation/scoring.py`
- Test: `backend/tests/test_recommendation/test_scoring.py`

**Consumes:** list[dict] POIs, weights dict, user preferences, center coordinates
**Produces:** scored + sorted POI list with "score" field

**Steps:**

1. Implement score_pois(pois, preferences, weights, center_lng, center_lat):
   - preference_score: Jaccard similarity (POI tags vs user preferences)
   - distance_score: 1.0 - haversine_km / 20.0 (capped at 0)
   - rating_score: rating / 5.0
   - time_score: 0.8 default (opening hours check)
   - popularity_score: review_count / max_review_count
   - total = weighted sum

2. Write tests:
   - test_scoring_prefers_matching_tags
   - test_scoring_prefers_closer_pois
   - test_scoring_prefers_higher_rated
   - test_scoring_sorts_descending

3. Run tests, commit: `feat: multi-factor scoring with Jaccard, distance, rating, popularity`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 3.3: MMR Diversity Rerank

**Files:**
- Create: `backend/recommendation/mmr.py`
- Test: `backend/tests/test_recommendation/test_mmr.py`

**Consumes:** scored POI list, lambda parameter, selection count
**Produces:** diverse POI subset

**Steps:**

1. Implement mmr_rerank(pois, lambda_=0.7, k=10):
   - For each iteration, select POI maximizing: lambda * relevance - (1-lambda) * max_similarity_to_selected
   - Similarity: category overlap (Jaccard)
   - Continue until k POIs selected or pool exhausted

2. Write tests:
   - test_mmr_selects_diverse_categories: input has 8 temples + 2 museums, MMR picks museums
   - test_mmr_respects_lambda_zero: lambda=0 -> pure diversity
   - test_mmr_respects_lambda_one: lambda=1 -> pure relevance

3. Run tests, commit: `feat: MMR diversity rerank for category-balanced recommendations`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 3.4: DBSCAN Clustering (Day Assignment)

**Files:**
- Create: `backend/recommendation/clustering.py`
- Test: `backend/tests/test_recommendation/test_clustering.py`

**Consumes:** POI list with lng/lat, number of days
**Produces:** list of day assignments: [{day: 1, pois: [...]}, ...]

**Steps:**

1. Implement cluster_pois_for_days(pois, n_days):
   - Extract (lat, lng) coordinates as numpy array
   - Try DBSCAN(eps=0.03, min_samples=2) -- ~3km in degrees
   - If DBSCAN produces wrong number of clusters, fallback to KMeans(n_clusters=n_days)
   - Sort clusters by centroid distance from city center
   - Map cluster index to day number

2. Write tests:
   - test_clustering_assigns_nearby_pois_same_day
   - test_clustering_splits_distant_pois
   - test_clustering_fallback_to_kmeans

3. Run tests, commit: `feat: DBSCAN clustering for day assignment with KMeans fallback`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 3.5: TSP Route Optimization

**Files:**
- Create: `backend/recommendation/tsp.py`
- Test: `backend/tests/test_recommendation/test_tsp.py`

**Consumes:** daily POI list
**Produces:** optimized visiting order + total distance

**Steps:**

1. Implement optimize_daily_route(pois):
   - Build distance matrix using haversine
   - Nearest neighbor heuristic starting from POI closest to city center
   - 2-opt improvement: iterate swaps until no improvement
   - Return ordered POI list + per-segment distances

2. Write tests:
   - test_tsp_reduces_total_distance_vs_input_order
   - test_tsp_preserves_all_pois
   - test_tsp_single_poi_returns_same

3. Run tests, commit: `feat: TSP optimization - nearest neighbor + 2-opt improvement`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 3.6: Recommendation Pipeline

**Files:**
- Create: `backend/recommendation/pipeline.py`
- Test: `backend/tests/test_recommendation/test_pipeline.py`

**Consumes:** All 5 steps above
**Produces:** run_recommendation_pipeline(city, preferences, days, weights, center) -> full plan

**Steps:**

1. Implement run_recommendation_pipeline():
   - Step 1: spatial_filter_pois() -> ~50 candidates
   - Step 2: score_pois() -> ~20 scored
   - Step 3: mmr_rerank() -> ~12 diverse
   - Step 4: cluster_pois_for_days() -> daily assignments
   - Step 5: optimize_daily_route() per day -> final routes

2. Write integration test:
   - test_full_pipeline_produces_daily_plans: mock spatial filter, verify pipeline structure
   - test_pipeline_returns_correct_number_of_days

3. Run tests, commit: `feat: recommendation pipeline - 5-step orchestration`

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 4: Backend API

### Task 4.1: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/poi.py` (POIResponse, POISearchRequest)
- Create: `backend/app/schemas/trip.py` (TripCreate, TripResponse, TripDetailResponse)
- Create: `backend/app/schemas/agent.py` (ChatRequest, ChatSSEEvent)
- Create: `backend/app/schemas/auth.py` (RegisterRequest, LoginRequest, TokenResponse)

**Steps:**
1. Define all Pydantic models matching the ORM models and API contracts
2. Commit: `feat: Pydantic schemas for all API endpoints`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 4.2: POI Service + API

**Files:**
- Create: `backend/app/services/poi_service.py`
- Create: `backend/app/api/v1/poi.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_api/test_poi_api.py`

**Steps:**
1. poi_service.py: search_pois(db, city, category?, keyword?, bbox?, rating_min?, page, size) -> paginated results
2. poi.py API: GET /api/v1/poi/search with query params
3. Response envelope: {success: true, data: {total, items: [...]}}
4. Write API test with mock DB
5. Commit: `feat: POI search API with spatial filtering`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 4.3: Agent Chat SSE API

**Files:**
- Create: `backend/app/api/v1/agent.py`
- Create: `backend/agent/checkpointer.py`
- Test: `backend/tests/test_api/test_agent_api.py`

**Steps:**
1. checkpointer.py: get_checkpointer() returns MemorySaver (dev) or PostgresSaver (prod)
2. agent.py: POST /api/v1/agent/chat with SSE response
   - Accept {session_id, message}
   - Build graph, invoke with state, stream SSE events from structured_plan
   - Each event: `event: message\ndata: {type, content}\n\n`
   - Final event: `event: done\ndata: {}\n\n`
3. Write API test verifying SSE stream
4. Commit: `feat: Agent chat API with SSE streaming`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 4.4: Trip CRUD API

**Files:**
- Create: `backend/app/services/trip_service.py`
- Create: `backend/app/api/v1/trip.py`
- Test: `backend/tests/test_api/test_trip_api.py`

**Steps:**
1. trip_service.py: create_trip, get_trip, list_trips, update_trip, delete_trip
2. trip.py API: POST/GET/PUT/DELETE /api/v1/trips
3. All endpoints require JWT auth (dependency injection)
4. Write tests
5. Commit: `feat: Trip CRUD API with user ownership`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 4.5: JWT Auth

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_api/test_auth_api.py`

**Steps:**
1. auth_service.py: hash_password, verify_password, create_token, decode_token
2. auth.py: POST /register, POST /login (returns JWT)
3. get_current_user dependency for protected endpoints
4. Write tests
5. Commit: `feat: JWT authentication - register, login, token validation`

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 5: Frontend WebGIS

### Task 5.1: Types + API Layer

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/agent.ts`, `poi.ts`, `trip.ts`, `auth.ts`

**Steps:**
1. types/index.ts: POI, Trip, DayPlan, ChatMessage, SSEEvent, ParsedIntent interfaces
2. api/agent.ts: sendChatMessage() using fetch + ReadableStream for SSE
3. api/poi.ts: searchPOIs()
4. api/trip.ts: CRUD functions
5. api/auth.ts: register(), login(), store token in localStorage
6. Commit: `feat: frontend types and API layer`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.2: Pinia Stores

**Files:**
- Create: `frontend/src/stores/chat.ts`, `map.ts`, `trip.ts`

**Steps:**
1. chat store: messages array, sessionId, sendMessage(), SSE handling
2. map store: pois array, routes array, selectedPOI, setPOIs(), setRoutes(), clearMap()
3. trip store: trips array, currentTrip, CRUD operations
4. Commit: `feat: Pinia stores for chat, map, trip state`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.3: MapView Component

**Files:**
- Create: `frontend/src/components/map/MapView.vue`
- Create: `frontend/src/components/map/PoiMarker.vue`

**Steps:**
1. MapView.vue: LMap with Amap tile layer, center/zoom from map store
2. PoiMarker.vue: LMarker with numbered divIcon, click to show popup
3. Auto-fit bounds when POIs change
4. Commit: `feat: MapView with Leaflet + Amap tiles and POI markers`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.4: Chat Panel

**Files:**
- Create: `frontend/src/components/chat/ChatPanel.vue`
- Create: `frontend/src/components/chat/MessageBubble.vue`

**Steps:**
1. ChatPanel.vue: message list + input area, SSE streaming
2. MessageBubble.vue: user/assistant styling, thinking/tool_calling states
3. Handle SSE events: update chat store, trigger map store updates
4. Commit: `feat: Chat panel with SSE streaming and message bubbles`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.5: Dialog-Map Linkage

**Files:**
- Modify: `frontend/src/stores/chat.ts` (SSE event handlers)
- Modify: `frontend/src/stores/map.ts` (auto-update from events)

**Steps:**
1. On poi_result SSE: map store.setPOIs(), MapView auto-marks
2. On route_result SSE: map store.setRoutes(), RouteLayer auto-draws
3. On plan_summary: show trip card
4. User clicks marker -> show info popup
5. Commit: `feat: dialog-map linkage - SSE events drive map updates`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.6: Route Visualization

**Files:**
- Create: `frontend/src/components/map/RouteLayer.vue`

**Steps:**
1. LPolyline per day with distinct colors (Day1: blue, Day2: green, Day3: orange)
2. Numbered markers at each POI along route
3. Distance/duration labels on segments
4. Commit: `feat: route visualization with per-day colored polylines`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.7: Trip Detail View

**Files:**
- Create: `frontend/src/components/trip/TripTimeline.vue`
- Create: `frontend/src/components/trip/DayCard.vue`
- Create: `frontend/src/views/TripDetailView.vue`

**Steps:**
1. TripTimeline: vertical timeline with DayCards
2. DayCard: POI cards in order with time, distance, transport info
3. TripDetailView: full page with timeline + mini map
4. Commit: `feat: trip detail view with timeline and day cards`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 5.8: HomeView Assembly

**Files:**
- Create: `frontend/src/views/HomeView.vue`
- Modify: `frontend/src/App.vue`

**Steps:**
1. HomeView: split layout - left 60% MapView, right 40% ChatPanel
2. Responsive: stack vertically on mobile
3. Add Vue Router: HomeView as default route
4. Commit: `feat: HomeView with map+chat split layout`

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 6: Integration

### Task 6.1: Seed Data

**Files:**
- Create: `data/seed/seed_hangzhou.py`, `data/seed/seed_chengdu.py`

**Steps:**
1. Prepare 20-30 POIs per city with real coordinates
2. Script to insert into PostGIS via SQLAlchemy
3. Run seed script, verify POIs queryable
4. Commit: `feat: seed data for Hangzhou and Chengdu`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 6.2: E2E Smoke Test

**Steps:**
1. Start Docker Compose, run seed data
2. Test: send "帮我规划杭州两日游" -> verify SSE stream with poi_result, route_result, text
3. Test: verify map shows markers and routes
4. Fix any integration issues
5. Commit: `test: end-to-end smoke test passing`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 6.3: Error Handling

**Steps:**
1. LLM timeout: retry once, then graceful error message
2. Amap API failure: fallback to local DB data
3. DB connection failure: retry with backoff
4. Frontend: show error notifications, retry buttons
5. Commit: `feat: error handling and graceful degradation`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 6.4: UI Polish

**Steps:**
1. Unified color scheme and typography
2. Loading animations for agent thinking
3. Responsive layout for mobile
4. Smooth map transitions
5. Commit: `feat: UI polish - styling, animations, responsive`

archived-with: 2026-06-29-ai-travel-planner
---

## PHASE 7: Testing & Demo

### Task 7.1: Backend Tests

**Steps:**
1. Recommendation engine unit tests (all 5 steps)
2. Agent integration tests (router + planner + formatter)
3. API endpoint tests
4. Target: 80%+ coverage
5. Commit: `test: backend test suite with 80%+ coverage`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 7.2: Frontend E2E

**Steps:**
1. Install Playwright
2. Write E2E tests: load map, send chat, verify markers appear
3. Test responsive layouts
4. Commit: `test: frontend E2E tests with Playwright`

archived-with: 2026-06-29-ai-travel-planner
---

### Task 7.3: Documentation + Demo Prep

**Steps:**
1. API documentation (auto-generated OpenAPI)
2. User manual with screenshots
3. Demo script with 5 test cases
4. Pre-record demo video as fallback
5. Commit: `docs: API docs, user manual, demo preparation`

archived-with: 2026-06-29-ai-travel-planner
---

## Execution Notes

- Each task ends with a commit
- TDD: write test first, see it fail, implement, see it pass
- After Phase 2, the agent pipeline works end-to-end (without real recommendation)
- After Phase 3, recommendation engine is testable independently
- After Phase 4, API is testable via curl/httpx
- After Phase 5, frontend is functional
- Phase 6-7 are integration and polish
