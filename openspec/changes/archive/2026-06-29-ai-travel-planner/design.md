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

适配层处理：Tool Calling 格式差异、流式输出 chunk 格式差异、模型能力降级（不支持 tool calling 时的 fallback）。

### D3: 空间推荐 — 算法驱动，非知识驱动

**决策**：不依赖预定义区域标签（如"西湖片区"），而是通过算法自动发现任何城市的空间结构。

推荐流程：
1. **空间过滤**：PostGIS `ST_DWithin` 筛选目标区域内的 POI
2. **多因子评分**：偏好匹配(0.3) + 空间距离(0.2) + 评分(0.2) + 时间适宜性(0.15) + 多样性(0.15)
3. **MMR 多样性重排**：避免推荐一堆同质景点
4. **空间聚类分天**：DBSCAN 将景点按地理邻近性分组到各天
5. **TSP 路线优化**：最近邻启发式 + 2-opt 改进，最小化总行程

### D4: 数据策略 — 种子兜底 + 实时查询

**决策**：预置 2-3 个热门城市种子数据 + 高德 API 实时查询，不限定城市。

- 本地 PostGIS 存储热门城市 POI（查询快、答辩安全）
- 本地无数据时自动 fallback 到高德 API
- Agent 工具中封装"先查本地，不足则调 API"的策略

### D5: 对话-地图联动协议

**决策**：Agent 返回结构化 JSON + 自然语言，前端分别渲染。

```
SSE 事件流:
data: {"type": "thinking", "content": "正在分析您的偏好..."}
data: {"type": "poi_result", "pois": [...], "display": "已找到12个景点"}
data: {"type": "route_result", "polylines": [...], "daily_plans": [...]}
data: {"type": "message", "content": "为您规划好杭州两日游..."}
```

前端收到 `poi_result` → 地图自动标注；收到 `route_result` → 地图绘制路线。

## Tech Stack

| 层 | 技术 | 理由 |
|----|------|------|
| 前端框架 | Vue 3 + Vite + TypeScript | 学习曲线友好，课设够用 |
| 地图引擎 | Leaflet + 高德瓦片 | 轻量、插件丰富、国内加载快 |
| UI 组件 | Element Plus | Vue 生态最成熟 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| 图表 | ECharts 5 | 偏好雷达图等可视化 |
| 后端框架 | FastAPI | 原生 async，自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | PostGIS 支持最好 |
| Agent 框架 | LangGraph | 状态图编排，流程可视化 |
| LLM | 通义千问 (DashScope) | 国内直连，中文强，免费 |
| 数据库 | PostgreSQL + PostGIS | 空间查询行业标准 |
| 缓存 | Redis | 热点 POI 缓存 |
| 部署 | Docker Compose | 一键启动 |

## Data Model

核心表：
- `poi` — 景点 POI（含 GEOMETRY 空间字段 + GIST 空间索引）
- `trip` — 行程
- `trip_day` — 日计划
- `trip_day_poi` — 日计划景点关联（有序）
- `chat_session` — 对话历史（JSONB 消息列表 + 上下文状态）
- `users` — 用户

## Project Structure

```
aiagent-travel/
├── frontend/          # Vue 3 前端
├── backend/
│   ├── app/           # FastAPI 应用
│   │   ├── api/v1/    # API 路由
│   │   ├── models/    # ORM 模型
│   │   ├── schemas/   # Pydantic 模型
│   │   └── services/  # 业务逻辑
│   └── agent/         # Agent 层
│       ├── graph.py   # LangGraph 状态图
│       ├── state.py   # Agent 状态定义
│       ├── nodes/     # 图节点（Router, Planner, Formatter）
│       └── tools/     # 工具链
├── data/              # 数据脚本和种子数据
└── docker-compose.yml
```
