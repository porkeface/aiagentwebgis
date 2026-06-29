# Task 5.6: Route Visualization

**Phase:** PHASE 5: Frontend WebGIS

**Files:**
- Create: `frontend/src/components/map/RouteLayer.vue`

**Steps:**
1. LPolyline per day with distinct colors (Day1: blue, Day2: green, Day3: orange)
2. Numbered markers at each POI along route
3. Distance/duration labels on segments
4. Commit: `feat: route visualization with per-day colored polylines`

---

## Context

**Parent Plan:** [AI Travel Planner Implementation Plan](../../docs/superpowers/plans/2026-06-29-ai-travel-planner.md)

**Architecture Context:**
- **Goal:** Build an AI Agent-based travel route planning and scenic spot recommendation system with WebGIS visualization.
- **Architecture:** Four-layer architecture (Frontend Vue3+Leaflet -> Backend FastAPI -> Agent LangGraph StateGraph -> Data PostgreSQL/PostGIS). Core brain is Planner Agent using ReAct pattern with shared State whiteboard. SSE streaming for real-time dialog-map linkage.
- **Tech Stack:** Vue 3 + Vite + TypeScript, Leaflet + Amap tiles, Element Plus, Pinia, FastAPI, SQLAlchemy 2.0 + GeoAlchemy2, LangGraph, Tongyi Qwen (DashScope), PostgreSQL + PostGIS, Redis, Docker Compose

**Global Constraints:**
- Python 3.11+, Node.js 18+
- All API responses use envelope: `{"success": bool, "data": any, "error": str|null}`
- All async endpoints use `async/await`
- SSE format: `event: message` then `data: {"type": "<msg_type>", "content": <any>}`
- PostGIS SRID: 4326 (WGS84)
- LLM temperature: 0.3
- Docker Compose for all services
- No hardcoded secrets, env vars only

**Dependencies (what this task consumes):**
- `frontend/src/stores/map.ts` — routes array, POIs array
- `frontend/src/types/index.ts` — POI, DayPlan, SSEEvent interfaces
- Task 5.2 (Pinia Stores) — map store with setRoutes()
- Task 5.3 (MapView) — LMap with Amap tile layer
- Task 5.5 (Dialog-Map Linkage) — route_result SSE events trigger route drawing

**Produces:**
- RouteLayer.vue component that renders per-day colored polylines on the map
- Numbered markers at each POI stop along the route
- Distance/duration labels on route segments

**Related Tasks:**
- Task 5.5 (Dialog-Map Linkage) — feeds route data into map store
- Task 5.7 (Trip Detail View) — may reuse route visualization patterns
- Task 5.8 (HomeView Assembly) — integrates MapView + RouteLayer

---

## Execution Instructions

1. Read the map store (`frontend/src/stores/map.ts`) to understand the route data structure
2. Read the types (`frontend/src/types/index.ts`) to understand POI and route interfaces
3. Create `frontend/src/components/map/RouteLayer.vue` with:
   - Props or store consumption for routes data (array of daily routes)
   - Color palette: Day1=#1890ff (blue), Day2=#52c41a (green), Day3=#fa8c16 (orange), Day4+ cycle
   - LPolyline for each day's route connecting POIs in order
   - Numbered divIcon markers at each POI stop (showing stop number within the day)
   - Tooltip or label on each polyline segment showing distance (km) and duration (min)
4. Ensure the component integrates with MapView.vue (rendered as a child/layer inside LMap)
5. Handle edge cases: empty routes, single POI (no polyline needed), route with only 2 POIs
6. Commit: `feat: route visualization with per-day colored polylines`
