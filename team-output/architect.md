# 架构设计文档

## 基于AI Agent的旅游路线智能规划与景点空间推荐系统

> **角色**：架构师
> **日期**：2026-06-29
> **状态**：初稿，待团队讨论

---

## 一、整体架构方案

### 1.1 架构总览

采用**四层分层架构**，各层职责清晰、可独立开发测试：

```
┌─────────────────────────────────────────────────────────┐
│                   前端 · WebGIS 可视化层                  │
│  Vue 3 + Vite + Leaflet + ECharts                       │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ 地图展示模块 │  │ AI 对话交互模块 │  │ 路线/行程展示模块 │  │
│  └────────────┘  └──────────────┘  └────────────────┘   │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────┐
│                   后端 · API 服务层                       │
│  Python FastAPI (async)                                 │
│  ┌────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐  │
│  │用户认证 │  │ POI 数据  │  │行程管理 │  │ Agent 网关  │  │
│  │模块    │  │ 服务模块  │  │模块    │  │ (SSE)      │  │
│  └────────┘  └──────────┘  └────────┘  └──────┬─────┘  │
└──────────────────────────────────────────────┬──────────┘
                                               │
┌──────────────────────────────────────────────▼──────────┐
│                   Agent · AI 决策层                      │
│  LangGraph Agent Orchestrator                           │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Trip Planner │  │ POI Advisor │  │ Route Optimizer│  │
│  │ Agent        │  │ Agent       │  │ Agent         │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │             Tool Layer (工具链)                    │   │
│  │  POI搜索 · 路径规划 · 地理编码 · 天气 · 推荐算法   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   数据层                                 │
│  ┌───────────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ PostgreSQL    │  │ Redis    │  │ 外部数据源       │  │
│  │ + PostGIS     │  │ 缓存层   │  │ 高德API / LLM   │  │
│  └───────────────┘  └──────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 各层职责

| 层级 | 核心职责 | 关键约束 |
|------|---------|---------|
| **前端可视化层** | 地图渲染、路线绘制、POI 标注、AI 对话交互、行程展示 | 不直接访问数据库，所有数据通过 API 层获取 |
| **API 服务层** | 用户认证、CRUD 操作、数据聚合、Agent 调度与流式响应 | 无状态（session 存 Redis），负责鉴权和限流 |
| **Agent 决策层** | 自然语言理解、多步推理、工具编排、路线规划、景点推荐 | 不直接面向用户，由 API 层调用，返回结构化结果 |
| **数据层** | POI 空间数据存储与查询、用户数据持久化、热点数据缓存 | 空间查询用 PostGIS，关系数据用 ORM |

### 1.3 层间交互协议

```
Frontend ──HTTP REST──► API Layer        (POI查询, 用户操作, 行程CRUD)
Frontend ──SSE────────► API Layer        (Agent 流式对话响应)
API Layer ──函数调用───► Agent Layer      (传入用户意图, 返回结构化结果)
Agent Layer ──HTTP────► External APIs    (高德地图API, LLM API)
Agent Layer ──SQL─────► Database         (通过DB工具查询POI)
API Layer ──ORM───────► Database         (用户数据, 行程数据)
API Layer ──TCP───────► Redis            (缓存, Session)
```

---

## 二、模块划分

### 2.1 项目目录结构

```
aiagent-travel/
├── frontend/                    # 前端项目 (Vue 3)
│   ├── src/
│   │   ├── views/               # 页面组件
│   │   │   ├── HomeView.vue
│   │   │   ├── PlanView.vue
│   │   │   └── TripDetailView.vue
│   │   ├── components/
│   │   │   ├── map/
│   │   │   │   ├── TravelMap.vue
│   │   │   │   ├── PoiMarker.vue
│   │   │   │   ├── RouteLayer.vue
│   │   │   │   └── MapControls.vue
│   │   │   ├── chat/
│   │   │   │   ├── ChatPanel.vue
│   │   │   │   ├── MessageBubble.vue
│   │   │   │   └── PlanCard.vue
│   │   │   └── trip/
│   │   │       ├── TimelineView.vue
│   │   │       └── DayPlan.vue
│   │   ├── stores/
│   │   │   ├── useMapStore.ts
│   │   │   ├── useChatStore.ts
│   │   │   └── useTripStore.ts
│   │   ├── composables/
│   │   │   ├── useGeolocation.ts
│   │   │   └── useSSE.ts
│   │   └── api/
│   │       ├── poi.ts
│   │       ├── trip.ts
│   │       └── agent.ts
│
├── backend/                     # 后端项目 (FastAPI)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── poi.py
│   │   │   ├── trip.py
│   │   │   └── agent.py            # Agent 对话接口 (SSE)
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── trip.py
│   │   │   └── poi.py
│   │   ├── schemas/
│   │   │   ├── poi.py
│   │   │   ├── trip.py
│   │   │   └── agent.py
│   │   ├── services/
│   │   │   ├── poi_service.py
│   │   │   ├── trip_service.py
│   │   │   └── recommendation.py
│   │   └── core/
│   │       ├── security.py
│   │       └── exceptions.py
│   ├── agent/                   # Agent 层 (独立包)
│   │   ├── graph.py                 # LangGraph 主图定义
│   │   ├── state.py                 # Agent 状态定义
│   │   ├── nodes/
│   │   │   ├── router.py
│   │   │   ├── planner.py
│   │   │   ├── poi_advisor.py
│   │   │   ├── route_optimizer.py
│   │   │   └── formatter.py
│   │   └── tools/
│   │       ├── poi_search.py
│   │       ├── geocoding.py
│   │       ├── route_planning.py
│   │       ├── weather.py
│   │       └── db_query.py
│   ├── migrations/
│   └── tests/
│
├── data/
│   ├── scripts/
│   │   ├── import_poi.py
│   │   └── init_db.sql
│   └── seed/
│
├── docker-compose.yml
└── README.md
```

---

## 三、数据架构

### 3.1 POI 数据来源

**推荐方案：高德 API 实时调用 + 本地种子数据兜底**

| 方案 | 优势 | 劣势 | 推荐度 |
|------|------|------|--------|
| **高德 API 实时调用** | 数据最新最全，覆盖全国 | 有 QPS 限制，依赖网络 | ⭐⭐⭐⭐⭐ |
| **高德 API 预爬 + 本地存储** | 离线可用，查询快 | 数据可能过时 | ⭐⭐⭐ |
| **OpenStreetMap** | 开源免费 | 中国数据不够完善 | ⭐⭐ |
| **自建种子数据集** | 可控 | 覆盖有限 | ⭐⭐⭐ |

### 3.2 核心表设计

```sql
-- POI 表 (空间数据)
CREATE TABLE poi (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    category    VARCHAR(50)  NOT NULL,
    subcategory VARCHAR(100),
    city        VARCHAR(50)  NOT NULL,
    address     VARCHAR(500),
    location    GEOMETRY(POINT, 4326) NOT NULL,
    rating      DECIMAL(2,1),
    price_level SMALLINT,
    description TEXT,
    tags        TEXT[],
    source      VARCHAR(20),
    extra_data  JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_poi_location ON poi USING GIST (location);
CREATE INDEX idx_poi_city     ON poi (city);
CREATE INDEX idx_poi_category ON poi (category);

-- 行程表
CREATE TABLE trip (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id),
    title       VARCHAR(200) NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    start_date  DATE,
    end_date    DATE,
    status      VARCHAR(20) DEFAULT 'draft',
    plan_data   JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 行程日计划表
CREATE TABLE trip_day (
    id          BIGSERIAL PRIMARY KEY,
    trip_id     BIGINT REFERENCES trip(id) ON DELETE CASCADE,
    day_number  SMALLINT NOT NULL,
    date        DATE
);

-- 行程景点关联表 (有序)
CREATE TABLE trip_day_poi (
    id           BIGSERIAL PRIMARY KEY,
    trip_day_id  BIGINT REFERENCES trip_day(id) ON DELETE CASCADE,
    poi_id       BIGINT REFERENCES poi(id),
    sort_order   SMALLINT NOT NULL,
    arrival_time TIME,
    stay_minutes SMALLINT,
    transport    VARCHAR(20)
);

-- 对话历史表
CREATE TABLE chat_session (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id),
    session_id  UUID NOT NULL,
    messages    JSONB NOT NULL DEFAULT '[]',
    context     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 四、技术选型总结

| 维度 | 最终选择 | 一句话理由 |
|------|---------|-----------|
| 前端框架 | Vue 3 + Vite | 学习曲线友好，课设够用 |
| 地图引擎 | Leaflet + 高德瓦片 | 轻量、插件丰富、国内快 |
| UI 组件库 | Element Plus | Vue 生态最成熟的 UI 库 |
| 后端框架 | FastAPI | 异步、自动文档、类型安全 |
| Agent 框架 | LangGraph | 流程可视化、精细控制 |
| LLM | 通义千问 (Qwen) | 国内直连、中文强、免费 |
| 数据库 | PostgreSQL + PostGIS | 空间查询行业标准 |
| ORM | SQLAlchemy + GeoAlchemy2 | PostGIS 支持最好的 Python ORM |
| 缓存 | Redis | 热点数据缓存 |
| 依赖管理 | uv (后端) + pnpm (前端) | 快速、可复现 |
| 部署 | Docker Compose | 一键启动，环境一致 |

---

## 五、Agent 状态流转图

```
                    ┌──────────────┐
                    │   START      │
                    │ 接收用户输入  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  意图识别节点  │
                    │ (Router)     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
      ┌───────▼─────┐ ┌───▼────┐ ┌────▼──────┐
      │ 路线规划流程 │ │景点推荐│ │ 信息查询   │
      │ (Planner)   │ │(Advisor)│ │ (General) │
      └───────┬─────┘ └───┬────┘ └────┬──────┘
              │            │            │
      ┌───────▼─────┐     │     ┌─────▼──────┐
      │ POI 搜索节点 │     │     │ LLM 直接回答│
      │ (Tool Call) │     │     └─────┬──────┘
      └───────┬─────┘     │           │
              │            │           │
      ┌───────▼─────┐     │           │
      │ 路线优化节点 │     │           │
      │(Optimization)│    │           │
      └───────┬─────┘     │           │
              │            │           │
              └────────────┼───────────┘
                           │
                    ┌──────▼───────┐
                    │  结果格式化   │
                    │  (Formatter) │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    END       │
                    │ 返回结构化结果 │
                    └──────────────┘
```

---

## 六、架构决策记录 (ADR)

### ADR-001: 选择 LangGraph 而非 CrewAI
- LangGraph 的状态图模型更适合路线规划这种有明确步骤的流程
- 状态可视化对答辩展示非常有利
- 更精细的流程控制

### ADR-002: 选择 PostgreSQL + PostGIS 而非 MongoDB
- PostGIS 是空间数据库的行业标准
- 空间函数丰富（距离计算、范围查询、路径构建）
- 答辩时体现技术深度

### ADR-003: 选择通义千问而非 OpenAI
- 国内直连，答辩现场不怕网络问题
- 中文能力强，旅游场景描述更自然
- 免费额度足够开发

---

*文档版本: v1.0 | 最后更新: 2026-06-29*
