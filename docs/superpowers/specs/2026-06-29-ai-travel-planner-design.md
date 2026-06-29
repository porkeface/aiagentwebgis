---
comet_change: ai-travel-planner
role: technical-design
canonical_spec: openspec
archived-with: 2026-06-29-ai-travel-planner
status: final
---

# Technical Design: AI Travel Planner

## 1. Architecture

### 1.1 Four-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend · Vue 3 + Leaflet                                  │
│  Map ←→ Chat Panel ←→ Timeline                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼──────────────────────────────────┐
│  Backend · FastAPI                                           │
│  POI Service │ Trip CRUD │ Agent Gateway (SSE) │ JWT Auth    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  Agent · LangGraph StateGraph                                │
│  Router → Planner Agent (ReAct + Tools) → Formatter          │
│  Tools: POI Search │ Route Planning │ Spatial Analysis │ ...  │
│  LLM: ChatTongyi (primary) + Prompt-based fallback           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  Data Layer                                                  │
│  PostgreSQL + PostGIS │ Redis Cache │ Amap API │ LLM API      │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Responsibilities

| Layer | Responsibility | Constraint |
|-------|---------------|------------|
| Frontend | Map rendering, route drawing, POI markers, chat UI, trip timeline | No direct DB access; all data via API |
| Backend | Auth, CRUD, data aggregation, Agent scheduling, SSE streaming | Stateless (session in Redis/Checkpoint) |
| Agent | NLU, multi-step reasoning, tool orchestration, route planning, recommendation | Not user-facing; called by API layer |
| Data | POI spatial storage/query, user persistence, hot data cache | Spatial queries via PostGIS |

## 2. Core Design Decisions

### D1: Agent Architecture — StateGraph Shared Whiteboard

All nodes share one State object. Each node reads full context, does its work, writes results back. Not a pipeline — it's a "whiteboard" pattern.

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]      # Full conversation history
    session_id: str
    intent: str                      # "trip_planning" | "poi_recommendation" | "general"
    city: str | None
    days: int | None
    preferences: list[str]
    companion_types: list[str]       # ["children", "elderly", ...]
    budget_level: int | None         # 1-5
    candidate_pois: list[dict]
    selected_pois: list[dict]
    daily_plans: list[dict]
    route_polylines: list[str]
    recommendation_weights: dict     # Agent dynamically sets these
    response_text: str
    structured_plan: dict | None
```

**Router Node**: Conditional routing based on intent classification.
- "trip_planning" → Planner Agent
- "poi_recommendation" → Planner Agent (lighter mode)
- "general" → Formatter (direct LLM response)

**Planner Agent**: Core brain. ReAct pattern with tool calling. Reads full State, autonomously decides which tools to call, writes results back to State. Key behavior:
- Parses user intent and extracts parameters
- Calls POI search tools to find candidates
- Calls spatial analysis tools for distance/clustering
- Configures recommendation weights based on user profile
- Produces daily plans with optimized routes

**Formatter Node**: Packages State into structured SSE output. Generates natural language summary + structured JSON for frontend rendering.

**Loop-back capability**: If route optimization finds excessive distances, Planner can be re-invoked to select different POIs.

### D2: LLM Adapter — Adapter Pattern with Fallback

```python
class BaseLLMAdapter(ABC):
    @abstractmethod
    async def chat(self, messages, tools=None) -> LLMResponse: ...

    @abstractmethod
    async def stream(self, messages, tools=None) -> AsyncIterator[LLMChunk]: ...

class TongyiAdapter(BaseLLMAdapter):
    """Primary: ChatTongyi via langchain-community"""
    async def chat(self, messages, tools=None):
        try:
            return await self._tool_call_chat(messages, tools)
        except (ToolCallFormatError, ParseError):
            return await self._prompt_based_fallback(messages, tools)

    async def _tool_call_chat(self, messages, tools):
        """Normal path: LangChain tool calling"""
        ...

    async def _prompt_based_fallback(self, messages, tools):
        """Fallback: Inject tool descriptions into prompt, parse JSON from response"""
        tool_descriptions = self._format_tools_as_prompt(tools)
        prompt = messages + [{"role": "system", "content": tool_descriptions}]
        response = await self._raw_chat(prompt)
        return self._parse_tool_calls_from_text(response)
```

**Supported adapters**: Tongyi (DashScope), OpenAI, Ollama (local). Switch via environment variable `LLM_PROVIDER`.

### D3: SSE Protocol — Unified Message Body

Transport layer (fixed):
```
event: message
data: {"type": "<msg_type>", "content": <any>}

event: done
data: {}
```

Message types:
| type | content | Frontend behavior |
|------|---------|-------------------|
| `thinking` | string | Show "thinking..." animation |
| `tool_calling` | string | Show tool status (e.g., "Searching POIs...") |
| `poi_result` | `{pois: [...], center: [lng,lat], zoom: int}` | Auto-mark POIs on map |
| `route_result` | `{polylines: [...], daily_plans: [...]}` | Auto-draw routes on map |
| `plan_summary` | `{title, days, overview, highlights}` | Show trip summary card |
| `text` | string (streaming chunks) | Render natural language text |
| `error` | `{code, message}` | Show error notification |

### D4: State Persistence — LangGraph Checkpoint

```python
# Development
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# Production
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver(connection_string=DATABASE_URL)

graph = workflow.compile(checkpointer=checkpointer)

# Usage
config = {"configurable": {"thread_id": session_id}}
result = graph.invoke({"messages": [user_msg]}, config)
```

**Separation of concerns**:
- LangGraph Checkpoint → Agent internal state (for Agent use)
- `chat_session` table → Conversation message history (for frontend display)

### D5: Spatial Recommendation Engine — 5-Step Pipeline

```
Input: city + preferences + days + companion_types
  │
  ├─ Step 1: Spatial Filter (PostGIS ST_DWithin)
  │   Filter POIs within city boundary + reasonable radius
  │   → Candidate set ~50 POIs
  │
  ├─ Step 2: Multi-Factor Scoring (Agent-configured weights)
  │   score = w1*preference_match + w2*distance + w3*rating
  │         + w4*time_suitability + w5*popularity
  │   Weights are dynamically set by Planner Agent based on user profile
  │   → Sorted ~20 POIs
  │
  ├─ Step 3: MMR Diversity Rerank (λ=0.7)
  │   Maximize relevance while maintaining category diversity
  │   → Selected ~10-15 POIs
  │
  ├─ Step 4: Spatial Clustering for Day Assignment (DBSCAN)
  │   Cluster POIs by geographic proximity
  │   eps=3km, min_samples=2
  │   Assign clusters to days
  │   → daily_pois: [{day1: [poi,...]}, {day2: [poi,...]}]
  │
  └─ Step 5: TSP Route Optimization (Nearest Neighbor + 2-opt)
      For each day, find optimal visiting order
      Minimize total travel distance
      → Final route with polylines
  │
Output: daily_plans [{day, pois[], route_polyline, distances, durations, transport}]
```

**Agent Dynamic Weight Configuration**:

| User Profile | preference | distance | rating | time | popularity |
|-------------|-----------|----------|--------|------|------------|
| Family (elderly/kids) | 0.25 | 0.15 | 0.25 | 0.25 | 0.10 |
| Solo backpacker | 0.35 | 0.30 | 0.10 | 0.10 | 0.15 |
| Culture enthusiast | 0.40 | 0.15 | 0.20 | 0.15 | 0.10 |
| Default | 0.30 | 0.20 | 0.20 | 0.15 | 0.15 |

### D6: Data Strategy — Seed Fallback + Real-time Query

```python
async def search_pois(city, keyword=None, category=None, limit=20):
    # 1. Query local PostGIS first
    results = await db_poi_search(city, keyword, category, limit)

    # 2. If insufficient, supplement with Amap API
    if len(results) < limit:
        amap_results = await amap_poi_search(city, keyword, category, limit - len(results))
        results.extend(amap_results)

    # 3. Deduplicate + sort by rating
    return deduplicate_and_sort(results)[:limit]
```

**Seed data**: Pre-load 2-3 popular cities (Hangzhou, Chengdu) into PostGIS for demo safety.

## 3. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Frontend framework | Vue 3 + Vite + TypeScript | Friendly learning curve |
| Map engine | Leaflet + Amap tiles | Lightweight, plugins, fast in China |
| UI library | Element Plus | Mature Vue ecosystem |
| State management | Pinia | Vue 3 official |
| Charts | ECharts 5 | Radar charts, preference viz |
| Backend framework | FastAPI | Native async, auto OpenAPI docs |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | Best PostGIS support |
| Agent framework | LangGraph | State graph, visual flow, fine control |
| LLM (primary) | Tongyi Qwen via DashScope | Domestic, Chinese-strong, free tier |
| Database | PostgreSQL + PostGIS | Spatial query industry standard |
| Cache | Redis | Hot POI caching |
| Deploy | Docker Compose | One-command startup |

## 4. API Design

### 4.1 Agent Chat (Core)

```
POST /api/v1/agent/chat
Body: {session_id, message, context?}
Response: SSE stream (unified message body protocol)
```

### 4.2 POI Search

```
GET /api/v1/poi/search?city=杭州&category=景点&bbox=...&rating_min=4.0&page=1&size=20
Response: {total, items: [{id, name, category, location, rating, tags, ...}]}
```

### 4.3 Trip CRUD

```
POST   /api/v1/trips          Create trip
GET    /api/v1/trips           List user trips
GET    /api/v1/trips/:id       Get trip detail
PUT    /api/v1/trips/:id       Update trip (manual adjustment)
DELETE /api/v1/trips/:id       Delete trip
```

### 4.4 Auth

```
POST /api/v1/auth/register    Register
POST /api/v1/auth/login       Login → JWT token
```

## 5. Risk Mitigation

| Risk | Probability | Mitigation |
|------|------------|------------|
| Tongyi tool_call format error | Medium | Prompt-based fallback (D2) |
| Amap API rate limit/timeout | Low | Seed data fallback + Redis cache |
| Agent output instability | Medium | Low temperature (0.3) + structured output validation + post-processing |
| DBSCAN clustering poor results | Medium | Configurable params + K-Means backup |
| Demo network failure | Low | Cache typical plans + pre-recorded video fallback |

## 6. Testing Strategy

### Unit Tests
- Recommendation engine: each pipeline step independently (spatial filter, scoring, MMR, clustering, TSP)
- LLM adapter: tool call parsing, fallback mechanism
- API endpoints: request/response validation

### Integration Tests
- Agent pipeline: simulate user input → verify tool call chain and output structure
- SSE protocol: verify all message types are correctly emitted
- Database: PostGIS spatial queries return correct results

### E2E Tests
- Core scenarios: one-day trip, multi-day trip, preference modification, route adjustment
- Frontend-backend integration: user input → Agent reasoning → map visualization

### Demo Stability
- Prepare 5+ fixed test cases
- Run each 10 times to ensure no failures
- Pre-record demo video as fallback

## 7. Implementation Order

```
Phase 1: Foundation (Week 1)
├─ Project scaffolding (Vue3 + FastAPI + Docker)
├─ Database schema + PostGIS setup
├─ Amap API wrapper
└─ LLM adapter (Tongyi + fallback)

Phase 2: Agent Core (Week 2)
├─ LangGraph StateGraph skeleton
├─ Tool chain implementation (6+ tools)
├─ Planner Agent (ReAct + tools)
└─ Formatter node

Phase 3: Spatial Engine (Week 3)
├─ PostGIS spatial queries
├─ Multi-factor scoring
├─ DBSCAN clustering
├─ TSP optimization
└─ Recommendation pipeline integration

Phase 4: API + Frontend (Week 4-5)
├─ REST API endpoints
├─ SSE Agent chat endpoint
├─ Leaflet map + POI markers
├─ Chat panel + SSE handling
├─ Map-dialog linkage
└─ Route visualization

Phase 5: Polish (Week 5-6)
├─ End-to-end testing
├─ Seed data preparation
├─ Error handling + graceful degradation
├─ UI polish
└─ Documentation + demo preparation
```
