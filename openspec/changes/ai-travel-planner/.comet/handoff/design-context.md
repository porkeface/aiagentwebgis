# Comet Design Handoff

- Change: ai-travel-planner
- Phase: design
- Mode: compact
- Context hash: 3dec20ce8406e3a0736e85f8385b5b2a24f1f19edef5021df8af9e4e1aac93bc

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/ai-travel-planner/proposal.md

- Source: openspec/changes/ai-travel-planner/proposal.md
- Lines: 1-62
- SHA256: 64c75d63b5379c7842a3366fd3ffe491ea62c3f63007e24c1c717f52c3a80e20

```md
## Why

旅游路线规划是一个多约束、多目标的复杂决策问题。现有旅游平台（携程、马蜂窝等）依赖用户手动搜索和筛选，缺乏智能化规划能力。虽然 LLM 旅游助手已能生成文字攻略，但它们无法进行真实的空间分析 — 不知道景点之间的实际距离、不会考虑地理空间连续性、无法在地图上可视化路线。

本项目构建一个"能看地图、会做空间分析的 AI 旅行规划师"，通过 AI Agent + WebGIS 的组合，让用户用自然语言描述旅行需求，系统自动完成空间分析、智能推荐和路线规划，并在地图上可视化展示完整方案。

## What Changes

### 新建系统（全新项目，无已有代码）

- **AI Agent 决策层**：基于 LangGraph StateGraph 构建多节点协作架构，包含 Router（意图路由）、Planner Agent（核心推理大脑，ReAct + 多工具调用）、Formatter（结果格式化）三个节点，共享 State 实现上下文同步
- **LLM 适配层**：适配器模式支持切换通义千问/GPT/其他 LLM，统一 Tool Calling 和流式输出接口
- **空间分析推荐引擎**：算法驱动的空间推荐，包含空间过滤（PostGIS）、空间聚类（DBSCAN）、路线优化（TSP 启发式），不依赖预定义区域标签
- **Agent 工具链**：POI 搜索、附近搜索、地理编码、路径规划、天气查询、空间 SQL 查询等 10+ 工具
- **WebGIS 前端**：Vue3 + Leaflet 地图可视化，支持 POI 标注、路线绘制、对话-地图双向联动
- **后端 API 服务**：FastAPI 异步服务，SSE 流式对话响应，RESTful 数据接口
- **空间数据库**：PostgreSQL + PostGIS 存储 POI 空间数据，支持空间索引和空间查询
- **数据策略**：预置热门城市种子数据兜底 + 高德 API 实时查询，不限定城市

## Capabilities

### New Capabilities

- `natural-language-intent`: 自然语言意图解析 — 从用户输入提取目的地、天数、偏好、同行人员、预算等结构化参数
- `spatial-poi-search`: 空间 POI 检索 — 基于地理范围、分类、评分等条件的景点搜索，结合本地 PostGIS 和高德 API
- `spatial-recommendation`: 空间感知推荐 — 多因子评分（偏好匹配 + 空间距离 + 评分 + 时间约束）+ MMR 多样性重排
- `route-planning`: 智能路线规划 — 空间聚类分天 + TSP 排序优化 + 时间窗约束调度
- `agent-orchestration`: Agent 协作编排 — LangGraph StateGraph 多节点协作，共享状态，条件路由，回环能力
- `llm-adapter`: LLM 适配层 — 适配器模式统一多家 LLM 的 Tool Calling 和流式输出接口
- `map-visualization`: 地图可视化 — Leaflet 地图上的 POI 标注、路线绘制、对话-地图联动
- `multi-turn-dialog`: 多轮对话管理 — 结构化对话状态追踪，上下文保持，需求逐步细化
- `api-service`: 后端 API 服务 — FastAPI 异步接口，SSE 流式响应，行程 CRUD

### Modified Capabilities

（无，这是全新项目）

## Impact

### 代码

- 全新项目，从零搭建前端（Vue3）、后端（FastAPI）、Agent 层（LangGraph）
- 约 15-20 个核心模块文件

### API

- REST API：POI 查询、行程 CRUD、用户认证
- SSE：Agent 流式对话响应
- 外部 API 依赖：高德地图（POI/路径/地理编码）、通义千问 DashScope（LLM）

### 依赖

- 前端：vue3, leaflet, vue-leaflet, pinia, element-plus, echarts
- 后端：fastapi, uvicorn, sqlalchemy, geoalchemy2, langgraph, langchain, dashscope
- 数据库：PostgreSQL + PostGIS
- 部署：Docker Compose

### 数据

- 高德地图 API Key（免费额度）
- 通义千问 DashScope API Key（免费额度）
- POI 种子数据（预置 2-3 个热门城市）
```

## openspec/changes/ai-travel-planner/design.md

- Source: openspec/changes/ai-travel-planner/design.md
- Lines: 1-161
- SHA256: 0eddb25881382f3be8cf262af2f5f9cfca2944b5ecbd34aaa00b430e28660303

[TRUNCATED]

```md
## Architecture Overview

四层分层架构，各层职责清晰：

```
┌─────────────────────────────────────────────────────┐
│            前端 · WebGIS 可视化层                      │
│   Vue 3 + Leaflet + Element Plus + ECharts           │
│   地图展示 │ AI 对话面板 │ 行程时间轴                    │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST + SSE
┌──────────────────────▼──────────────────────────────┐
│            后端 · API 服务层                           │
│   FastAPI (async) + SQLAlchemy + GeoAlchemy2          │
│   POI服务 │ 行程管理 │ Agent网关(SSE) │ 认证           │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            Agent · AI 决策层                          │
│   LangGraph StateGraph                                │
│   ┌────────┐   ┌────────────┐   ┌──────────┐        │
│   │ Router  │──▶│  Planner   │──▶│Formatter │        │
│   │(条件路由)│   │  Agent     │   │(格式化)   │        │
│   └────────┘   │  (核心大脑) │   └──────────┘        │
│                │  ReAct+Tools │                       │
│                └──────┬───────┘                       │
│         ┌─────────────┼─────────────┐                │
│         │             │             │                │
│    ┌────▼───┐   ┌─────▼────┐  ┌────▼───┐          │
│    │POI搜索 │   │路径规划   │  │空间分析 │  ← 工具链 │
│    └────────┘   └──────────┘  └────────┘          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            数据层                                     │
│   PostgreSQL + PostGIS │ Redis 缓存 │ 高德API/LLM    │
└─────────────────────────────────────────────────────┘
```

## Key Design Decisions

### D1: Agent 架构 — StateGraph 共享白板模式

**决策**：采用 LangGraph StateGraph，核心推理集中在 Planner Agent，Router 和 Formatter 为辅助节点。

**不是流水线**。所有节点共享同一个 State 对象（共享白板），每个节点读取完整上下文、做自己的工作、写回结果。Planner Agent 是核心大脑，使用 ReAct 模式（推理 + 工具调用）自主决策。

```
共享 State = {
  messages: [...],          # 完整对话历史
  intent: "...",            # 识别的意图
  city: "...",              # 提取的城市
  preferences: [...],       # 用户偏好
  candidate_pois: [...],    # 候选景点
  selected_pois: [...],     # 选中的景点
  daily_plans: [...],       # 每日计划
  route_data: {...},        # 路线数据
}
```

**回环能力**：Route Optimizer 发现景点间距离过远时，可以回到 Planner 重新选择景点，而非单向流水线。

### D2: LLM 适配层 — 适配器模式

**决策**：抽象统一的 LLM 接口，支持运行时切换。

```
Agent 业务逻辑
      │
      │ 统一接口: chat() / tool_call() / stream()
      │
┌─────▼──────────┐
│   LLM Adapter  │
└──┬──────┬──────┘
   │      │
┌──▼──┐ ┌─▼──────┐
│通义千问│ │GPT/其他 │
└─────┘ └────────┘
```

```

Full source: openspec/changes/ai-travel-planner/design.md

## openspec/changes/ai-travel-planner/tasks.md

- Source: openspec/changes/ai-travel-planner/tasks.md
- Lines: 1-50
- SHA256: 51a9d39ec37c1f54804277acc84082f5ba521c86b2a618ad91779d991a15d009

```md
# Tasks — ai-travel-planner

## Phase 1: 项目基础搭建

- [ ] **T1.1 项目脚手架初始化** — 创建前端（Vue3 + Vite + TypeScript）和后端（FastAPI）项目结构，配置 ESLint、Prettier、Docker Compose
- [ ] **T1.2 数据库设计与建表** — PostgreSQL + PostGIS 建表（poi, trip, trip_day, trip_day_poi, chat_session, users），创建空间索引，Alembic 迁移配置
- [ ] **T1.3 高德 API 集成封装** — 封装高德 POI 搜索、路径规划、地理编码 API 为 Python 服务类，统一错误处理和限流
- [ ] **T1.4 LLM 适配层** — 实现 LLM Adapter 抽象接口（chat/tool_call/stream），完成通义千问 DashScope 适配器实现

## Phase 2: Agent 核心能力

- [ ] **T2.1 LangGraph 状态图骨架** — 定义 AgentState（TypedDict），构建 StateGraph，实现 Router 节点（意图分类 + 条件路由）
- [ ] **T2.2 Agent 工具链实现** — 实现 6+ 核心工具：search_pois, search_nearby, geocode, plan_route, query_db_pois, get_weather，注册到 LangGraph
- [ ] **T2.3 Planner Agent 核心推理** — 实现 Planner 节点：ReAct 模式，自主调用工具，从用户意图到完整行程方案
- [ ] **T2.4 Formatter 节点** — 实现结果格式化：将结构化行程数据 + 自然语言描述打包为 SSE 事件流

## Phase 3: 空间分析与推荐

- [ ] **T3.1 空间 POI 检索** — 基于 PostGIS 实现空间范围查询（ST_DWithin/ST_Within），结合高德 API 兜底
- [ ] **T3.2 多因子推荐评分** — 实现推荐评分算法：偏好匹配(0.3) + 空间距离(0.2) + 评分(0.2) + 时间适宜性(0.15) + 多样性(0.15)
- [ ] **T3.3 空间聚类分天** — 实现 DBSCAN 或 K-Means 对景点按地理坐标聚类，将景点分配到各天行程
- [ ] **T3.4 路线优化算法** — 实现 TSP 最近邻启发式 + 2-opt 改进，最小化每日行程总距离

## Phase 4: 后端 API

- [ ] **T4.1 POI 查询接口** — GET /api/v1/poi/search（支持城市、分类、空间范围、评分筛选）
- [ ] **T4.2 Agent 对话接口** — POST /api/v1/agent/chat（SSE 流式响应，支持多轮对话 session）
- [ ] **T4.3 行程 CRUD 接口** — POST/GET/PUT/DELETE /api/v1/trips（行程创建、查询、更新、删除）
- [ ] **T4.4 用户认证** — JWT 认证，注册/登录接口

## Phase 5: 前端 WebGIS

- [ ] **T5.1 地图主界面** — Leaflet 地图加载（高德瓦片），基础控件，POI 标注点展示
- [ ] **T5.2 AI 对话面板** — 聊天 UI 组件，SSE 流式消息接收，消息气泡渲染
- [ ] **T5.3 对话-地图联动** — 收到 poi_result 自动标注地图，收到 route_result 自动绘制路线
- [ ] **T5.4 路线可视化** — 地图上绘制带顺序编号的路线，不同天数不同颜色，标注距离和时间
- [ ] **T5.5 行程详情视图** — 时间轴展示每日行程，景点卡片，交通方式和时间

## Phase 6: 联调与打磨

- [ ] **T6.1 前后端联调** — 完整流程跑通：用户输入 → Agent 推理 → 地图可视化
- [ ] **T6.2 种子数据准备** — 准备 2-3 个热门城市（杭州、成都等）的 POI 种子数据导入数据库
- [ ] **T6.3 错误处理与兜底** — LLM 超时/失败兜底、API 限流处理、优雅降级
- [ ] **T6.4 UI 美化** — 整体 UI 风格统一，响应式布局，加载动画

## Phase 7: 测试与答辩准备

- [ ] **T7.1 端到端测试** — 覆盖核心场景：一日游规划、多日游规划、偏好修改、路线调整
- [ ] **T7.2 文档编写** — 系统架构图、Agent 流程图、API 文档、用户操作手册
- [ ] **T7.3 答辩演示准备** — 演示脚本编写、边界 case 处理、预录演示视频兜底
```

## openspec/changes/ai-travel-planner/specs/agent-orchestration/spec.md

- Source: openspec/changes/ai-travel-planner/specs/agent-orchestration/spec.md
- Lines: 1-63
- SHA256: fcbd054dd79f32dd19af7f0e9264aee3b88ac9d878acb857d5479a92f2893626

```md
# Capability: Agent Orchestration

## Overview

LangGraph StateGraph-based multi-node agent collaboration with shared state, conditional routing, and loop-back capability.

## State Schema

```typescript
AgentState = {
  messages: BaseMessage[]           // Full conversation history
  session_id: string
  intent: "trip_planning" | "poi_recommendation" | "general"
  city: string | null
  days: number | null
  preferences: string[]
  companion_types: string[]         // ["children", "elderly", "solo", ...]
  budget_level: number | null       // 1-5
  candidate_pois: POI[]
  selected_pois: POI[]
  daily_plans: DayPlan[]
  route_polylines: string[]
  recommendation_weights: WeightConfig
  response_text: string
  structured_plan: PlanSummary | null
}
```

## Nodes

### Router
- **Input**: User message from `messages[-1]`
- **Logic**: Classify intent using LLM (trip_planning / poi_recommendation / general)
- **Output**: Set `intent` field, route to appropriate next node
- **Routing**:
  - `trip_planning` → Planner
  - `poi_recommendation` → Planner (lighter mode, fewer tools)
  - `general` → Formatter (direct LLM response)

### Planner Agent
- **Input**: Full AgentState
- **Logic**: ReAct loop — reason about user needs, call tools, collect results
- **Tool access**: All registered tools (POI search, geocoding, route planning, weather, spatial analysis)
- **Output**: Updates `candidate_pois`, `selected_pois`, `daily_plans`, `recommendation_weights`, `response_text`
- **Loop-back**: If daily plan has excessive total distance (> threshold), re-invoke with constraint to select different POIs

### Formatter
- **Input**: Completed AgentState with all planning results
- **Logic**: Package structured data into SSE message sequence
- **Output**: Emit `poi_result`, `route_result`, `plan_summary`, `text` messages in order

## State Persistence

- Development: `MemorySaver` (in-memory)
- Production: `PostgresSaver` (PostgreSQL-backed)
- Access pattern: `graph.invoke(input, config={"configurable": {"thread_id": session_id}})`

## Acceptance Scenarios

1. User says "帮我规划杭州两日游" → Router classifies as trip_planning → Planner executes full pipeline → Formatter outputs complete plan
2. User says "杭州有什么好吃的" → Router classifies as poi_recommendation → Planner searches food POIs → Formatter outputs recommendation list
3. User says "你好" → Router classifies as general → Formatter returns greeting
4. Route optimization finds day 1 has 45km total → Loop back to Planner → Planner selects closer POIs → Re-optimization succeeds
```

## openspec/changes/ai-travel-planner/specs/llm-adapter/spec.md

- Source: openspec/changes/ai-travel-planner/specs/llm-adapter/spec.md
- Lines: 1-67
- SHA256: fa14ec1891bc0fc18c34c5cc9363b199de9141a6de194a4cd9c14a5d5ef5ba2a

```md
# Capability: LLM Adapter

## Overview

Adapter pattern providing unified LLM interface with fallback mechanism. Supports runtime switching between providers.

## Interface

```python
class BaseLLMAdapter(ABC):
    async def chat(self, messages: list[dict], tools: list[Tool] | None = None) -> LLMResponse
    async def stream(self, messages: list[dict], tools: list[Tool] | None = None) -> AsyncIterator[LLMChunk]

class LLMResponse:
    content: str
    tool_calls: list[ToolCall] | None
    usage: dict  # {prompt_tokens, completion_tokens}

class ToolCall:
    id: str
    name: str
    arguments: dict
```

## Implementations

### TongyiAdapter (Primary)
- Uses `langchain_community.chat_models.ChatTongyi`
- Normal path: LangChain tool calling (function call format)
- Fallback path: When tool_call parsing fails, inject tool descriptions into system prompt, request JSON output, parse with regex/JSON

### OpenAIAdapter
- Uses `langchain_openai.ChatOpenAI`
- Standard tool calling support

### OllamaAdapter
- Uses `langchain_community.chat_models.ChatOllama`
- For local development/testing without API keys

## Provider Selection

```python
# Via environment variable
LLM_PROVIDER=tongyi  # or openai, ollama

# Via factory function
def get_llm_adapter() -> BaseLLMAdapter:
    provider = os.getenv("LLM_PROVIDER", "tongyi")
    adapters = {"tongyi": TongyiAdapter, "openai": OpenAIAdapter, "ollama": OllamaAdapter}
    return adapters[provider]()
```

## Fallback Mechanism

When tool_call response format is invalid:
1. Log the error and raw response
2. Construct a prompt that describes available tools in natural language
3. Request the LLM to output tool calls as JSON in its response text
4. Parse the JSON from response text
5. If parsing still fails, return error message to user

## Acceptance Scenarios

1. TongyiAdapter receives valid tool_call response → parsed normally → tool executed
2. TongyiAdapter receives malformed tool_call → fallback triggered → prompt-based extraction succeeds
3. Fallback also fails → graceful error message returned to user
4. Switch LLM_PROVIDER from tongyi to openai → same agent code works without changes
```

## openspec/changes/ai-travel-planner/specs/map-visualization/spec.md

- Source: openspec/changes/ai-travel-planner/specs/map-visualization/spec.md
- Lines: 1-41
- SHA256: 29b632b44552dd97600416386d99e2b9ff46c77d4972f17b66b6ae4ba7bb5b0c

```md
# Capability: Map Visualization

## Overview

Leaflet-based map visualization with POI markers, route drawing, and bidirectional linkage with AI dialog panel.

## Map Layers

| Layer | Content | Trigger |
|-------|---------|---------|
| Base | Amap tile layer | Always visible |
| POI markers | Attractions with numbered icons | On `poi_result` SSE message |
| Route polylines | Colored lines connecting POIs in order | On `route_result` SSE message |
| Cluster highlights | Semi-transparent area overlays | Optional, on spatial analysis display |

## Dialog-Map Linkage

### Backend → Frontend (Agent output drives map)
- Receive `poi_result` → Auto-mark POIs on map with numbered markers
- Receive `route_result` → Auto-draw colored polylines for each day's route
- Receive `plan_summary` → Show trip overview card
- Map auto-zooms/centers to fit all markers

### Frontend → Backend (User map interaction triggers Agent)
- User clicks POI marker → Show info popup with details
- User drags marker to reorder → Send reorder request → Agent re-optimizes route
- User clicks "replace POI" → Agent searches nearby alternatives

## Route Visualization

- Each day has a distinct color (Day 1: blue, Day 2: green, Day 3: orange, ...)
- Markers are numbered (1, 2, 3...) within each day
- Polylines show direction arrows
- Distance and duration labels on each segment

## Acceptance Scenarios

1. Agent outputs poi_result with 10 POIs → 10 numbered markers appear on map, map auto-zooms to fit
2. Agent outputs route_result with 2 days → 2 colored polylines drawn, Day 1 blue with markers 1-5, Day 2 green with markers 1-5
3. User clicks marker 3 on Day 1 → Info popup shows POI name, rating, description, opening hours
4. User drags marker 5 to position 2 → Route re-calculated, polyline updated, new order displayed
```

## openspec/changes/ai-travel-planner/specs/natural-language-intent/spec.md

- Source: openspec/changes/ai-travel-planner/specs/natural-language-intent/spec.md
- Lines: 1-35
- SHA256: 936c6599018f7ee778020a13b07549258a1d836e2cbb895fb2439b94d212266e

```md
# Capability: Natural Language Intent Parsing

## Overview

Extract structured travel parameters from user's natural language input using LLM-based intent recognition.

## Extraction Schema

```python
class ParsedIntent:
    intent: Literal["trip_planning", "poi_recommendation", "general"]
    city: str | None
    days: int | None
    preferences: list[str]         # ["自然风光", "美食", "历史文化"]
    companion_types: list[str]     # ["children", "elderly", "solo", "couple"]
    budget_level: int | None       # 1-5
    start_date: str | None         # YYYY-MM-DD or relative ("明天", "五一")
    transport_mode: str | None     # "walking" | "driving" | "transit"
    constraints: list[str]         # ["不想太累", "避开人多"]
```

## Multi-Turn Context Accumulation

- First turn: "去杭州玩两天" → city=杭州, days=2
- Second turn: "带老人和小孩" → companion_types=["elderly", "children"] (added to existing context)
- Third turn: "不要去太远的地方" → constraints=["不想太累"] (added, preferences refined)

The AgentState accumulates parsed parameters across turns. Each turn's parsed result is merged into existing state, not replaced.

## Acceptance Scenarios

1. "帮我规划杭州两日游，喜欢自然风景和美食" → city=杭州, days=2, preferences=[自然风光, 美食]
2. "五一带爸妈和孩子去厦门" → city=厦门, start_date=五一, companion_types=[elderly, children]
3. "只有半天时间，推荐附近值得去的地方" → days=0.5, intent=poi_recommendation
4. Multi-turn: "去成都" → "玩三天" → "预算中等" → city=成都, days=3, budget_level=3
```

## openspec/changes/ai-travel-planner/specs/spatial-recommendation/spec.md

- Source: openspec/changes/ai-travel-planner/specs/spatial-recommendation/spec.md
- Lines: 1-56
- SHA256: d153d601a8f12c43996edc4f3e47585b14d215028c631588a07d02a4d43a3821

```md
# Capability: Spatial Recommendation Engine

## Overview

5-step recommendation pipeline: spatial filtering → multi-factor scoring → MMR diversity reranking → spatial clustering for day assignment → TSP route optimization.

## Step 1: Spatial Filter

- **Input**: city name, optional bounding box
- **Process**: Query PostGIS with `ST_DWithin(location, center_point, radius)` or `ST_Within(location, city_boundary)`
- **Fallback**: If local data insufficient, supplement with Amap API
- **Output**: Candidate POI list (~50 POIs)

## Step 2: Multi-Factor Scoring

- **Scoring formula**: `score = w1*preference + w2*distance + w3*rating + w4*time + w5*popularity`
- **Weights**: Dynamically configured by Planner Agent based on user profile
- **Default weights**: preference=0.30, distance=0.20, rating=0.20, time=0.15, popularity=0.15
- **Each factor normalized to [0, 1]**:
  - `preference`: Jaccard similarity between POI tags and user preferences
  - `distance`: Inverse distance from city center / hotel (normalized)
  - `rating`: POI rating / 5.0
  - `time`: Binary (open now?) or seasonal suitability score
  - `popularity`: Normalized review count or visit frequency
- **Output**: Scored and sorted POI list (~20 POIs)

## Step 3: MMR Diversity Rerank

- **Algorithm**: Maximal Marginal Relevance
- **Formula**: `MMR(d) = argmax [λ * Relevance(d) - (1-λ) * max_sim(d, selected)]`
- **λ = 0.7**: Balance between relevance and diversity
- **Similarity**: Category overlap between POIs
- **Output**: Diverse selected POI list (~10-15 POIs)

## Step 4: Spatial Clustering (Day Assignment)

- **Algorithm**: DBSCAN on (latitude, longitude)
- **Parameters**: eps=3km, min_samples=2
- **Fallback**: If DBSCAN produces poor clusters (too few or too many), fall back to K-Means with k=days
- **Cluster-to-day mapping**: Sort clusters by centroid distance from hotel/city center, assign to Day 1, Day 2, etc.
- **Output**: `daily_pois: [{day: 1, pois: [...]}, {day: 2, pois: [...]}]`

## Step 5: TSP Route Optimization

- **Algorithm**: Nearest Neighbor heuristic → 2-opt improvement
- **Input**: Daily POI list per day
- **Distance matrix**: Computed via Amap walking/driving API (or Haversine for MVP)
- **Constraints**: Opening hours (time window), estimated stay duration
- **Output**: Optimized visiting order + polyline + per-segment distance/duration

## Acceptance Scenarios

1. City with 100 POIs → spatial filter reduces to ~50 → scoring selects top 20 → MMR picks 12 → clustering assigns 6 per day → TSP optimizes order
2. User with elderly companions → Agent sets distance weight=0.15, time weight=0.25 → flatter, more accessible POIs ranked higher
3. Two POIs same category "temple" within 500m → MMR ensures only one is selected unless user specifically wants temples
4. Day 1 cluster has POIs spanning 15km → DBSCAN eps=3km would split → correctly assigns to separate days or uses K-Means fallback
```

