# Tasks — ai-travel-planner

## Phase 1: 项目基础搭建

- [x] **T1.1 项目脚手架初始化** — 创建前端（Vue3 + Vite + TypeScript）和后端（FastAPI）项目结构，配置 ESLint、Prettier、Docker Compose
- [x] **T1.2 数据库设计与建表** — PostgreSQL + PostGIS 建表（poi, trip, trip_day, trip_day_poi, chat_session, users），创建空间索引，Alembic 迁移配置
- [x] **T1.3 高德 API 集成封装** — 封装高德 POI 搜索、路径规划、地理编码 API 为 Python 服务类，统一错误处理和限流
- [x] **T1.4 LLM 适配层** — 实现 LLM Adapter 抽象接口（chat/tool_call/stream），完成通义千问 DashScope 适配器实现

## Phase 2: Agent 核心能力

- [x] **T2.1 LangGraph 状态图骨架** — 定义 AgentState（TypedDict），构建 StateGraph，实现 Router 节点（意图分类 + 条件路由）
- [x] **T2.2 Agent 工具链实现** — 实现 6+ 核心工具：search_pois, search_nearby, geocode, plan_route, query_db_pois, get_weather，注册到 LangGraph
- [x] **T2.3 Planner Agent 核心推理** — 实现 Planner 节点：ReAct 模式，自主调用工具，从用户意图到完整行程方案
- [x] **T2.4 Formatter 节点** — 实现结果格式化：将结构化行程数据 + 自然语言描述打包为 SSE 事件流

## Phase 3: 空间分析与推荐

- [x] **T3.1 空间 POI 检索** — 基于 PostGIS 实现空间范围查询（ST_DWithin/ST_Within），结合高德 API 兜底
- [x] **T3.2 多因子推荐评分** — 实现推荐评分算法：偏好匹配(0.3) + 空间距离(0.2) + 评分(0.2) + 时间适宜性(0.15) + 多样性(0.15)
- [x] **T3.3 空间聚类分天** — 实现 DBSCAN 或 K-Means 对景点按地理坐标聚类，将景点分配到各天行程
- [x] **T3.4 路线优化算法** — 实现 TSP 最近邻启发式 + 2-opt 改进，最小化每日行程总距离

## Phase 4: 后端 API

- [x] **T4.1 POI 查询接口** — GET /api/v1/poi/search（支持城市、分类、空间范围、评分筛选）
- [x] **T4.2 Agent 对话接口** — POST /api/v1/agent/chat（SSE 流式响应，支持多轮对话 session）
- [x] **T4.3 行程 CRUD 接口** — POST/GET/PUT/DELETE /api/v1/trips（行程创建、查询、更新、删除）
- [x] **T4.4 用户认证** — JWT 认证，注册/登录接口

## Phase 5: 前端 WebGIS

- [x] **T5.1 地图主界面** — Leaflet 地图加载（高德瓦片），基础控件，POI 标注点展示
- [x] **T5.2 AI 对话面板** — 聊天 UI 组件，SSE 流式消息接收，消息气泡渲染
- [x] **T5.3 对话-地图联动** — 收到 poi_result 自动标注地图，收到 route_result 自动绘制路线
- [x] **T5.4 路线可视化** — 地图上绘制带顺序编号的路线，不同天数不同颜色，标注距离和时间
- [x] **T5.5 行程详情视图** — 时间轴展示每日行程，景点卡片，交通方式和时间

## Phase 6: 联调与打磨

- [x] **T6.1 前后端联调** — 完整流程跑通：用户输入 → Agent 推理 → 地图可视化
- [x] **T6.2 种子数据准备** — 准备 2-3 个热门城市（杭州、成都等）的 POI 种子数据导入数据库
- [x] **T6.3 错误处理与兜底** — LLM 超时/失败兜底、API 限流处理、优雅降级
- [x] **T6.4 UI 美化** — 整体 UI 风格统一，响应式布局，加载动画

## Phase 7: 测试与答辩准备

- [x] **T7.1 端到端测试** — 覆盖核心场景：一日游规划、多日游规划、偏好修改、路线调整
- [x] **T7.2 文档编写** — 系统架构图、Agent 流程图、API 文档、用户操作手册
- [x] **T7.3 答辩演示准备** — 演示脚本编写、边界 case 处理、预录演示视频兜底
