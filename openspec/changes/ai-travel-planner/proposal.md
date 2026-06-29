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
