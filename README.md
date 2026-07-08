# AI Travel Planner

基于 AI Agent 的旅游路线智能规划与景点空间推荐系统。用户以自然语言描述旅行需求，系统自动完成 POI 搜索、空间分天、路线优化，并在高德地图上可视化展示。

## 特性

- **AI 对话规划**：自然语言描述需求，AI 自动生成多日行程方案
- **确定性规划流水线**：十步流水线（搜索→评分→分区→路径→验证），结果可复现
- **高德地图可视化**：POI 标注、每日路线绘制、按类别着色区分
- **SSE 流式推送**：20种事件类型实时反馈 Agent 推理进度
- **多 LLM 支持**：DashScope（通义千问）/ DeepSeek，管理后台一键切换
- **配置热重载**：LLM Key/模型/高德 Key 修改后立即生效，无需重启
- **管理后台**：模型配置、高德 Key 管理、用户管理、数据统计
- **地图选点规划**：在首页地图上预选 POI，一键发起智能规划

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + 高德 JS API 2.0 |
| 后端 | FastAPI + SQLAlchemy 2.0 + GeoAlchemy2 |
| Agent | LangGraph StateGraph + ChatOpenAI（OpenAI 兼容接口） |
| 数据库 | PostgreSQL 15+ + PostGIS 3.3+ |
| 地图 | 高德地图 Web 服务 API + JS API |
| LLM | 通义千问（DashScope）/ DeepSeek |
| 状态管理 | Pinia |
| 包管理 | uv（Python）/ npm（Node） |

## 项目结构

```
aiagentwebgis/
├── backend/
│   ├── agent/                  # LangGraph Agent
│   │   ├── graph_v2.py         # StateGraph 编排（5节点）
│   │   ├── state.py            # AgentState 定义
│   │   ├── tools/              # 7个 Agent 工具
│   │   ├── prompts/            # System Prompt
│   │   └── checkpointer.py     # LangGraph 状态持久化
│   ├── app/
│   │   ├── api/v1/             # API 路由（auth/agent/poi/trip/admin/chat）
│   │   ├── models/             # 6张数据表 SQLAlchemy 模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务逻辑（amap/auth/config/chat）
│   │   ├── main.py             # FastAPI 应用工厂 + 速率限制中间件
│   │   ├── config.py           # Pydantic Settings（环境变量驱动）
│   │   └── database.py         # 异步数据库会话管理
│   ├── tests/                  # pytest 测试
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/                # API 客户端（agent/admin/auth/trips）
│   │   ├── components/map/     # 地图组件（MapView/RouteLayer/POIDetailCard 等）
│   │   ├── stores/             # Pinia Stores（chat/map/admin）
│   │   ├── views/              # 页面（首页/行程详情/管理后台）
│   │   ├── types/              # TypeScript 类型定义
│   │   └── utils/              # 工具函数（常量/格式化/高德加载）
│   └── package.json
├── scripts/
│   └── init_admin.py           # 初始化管理员账户
├── docs/
│   ├── reports/                # 五份设计报告
│   │   ├── 01-可行性研究报告.md
│   │   ├── 02-需求分析报告.md
│   │   ├── 03-概要设计报告.md
│   │   ├── 04-详细设计报告.md
│   │   └── 05-数据库设计报告.md
│   ├── user-manual.md          # 用户手册
│   └── demo-script.md          # 演示测试脚本
├── .env.example                # 环境变量模板
└── .gitignore
```

## 快速开始

### 前提条件

- **Python 3.11+** + **uv**（Python 包管理器）
- **Node.js 18+** + **npm**
- **PostgreSQL 15+** with **PostGIS 3.3+**
- [高德地图 API Key](https://lbs.amap.com/)（Web服务 + JS API 各一个）
- LLM API Key（[DashScope](https://dashscope.console.aliyun.com/) 或 [DeepSeek](https://platform.deepseek.com/)）

### 1. 配置数据库

在 PostgreSQL 中创建用户和数据库，并启用 PostGIS 扩展：

```sql
CREATE USER travel_planner WITH PASSWORD 'your_password';
CREATE DATABASE travel_planner OWNER travel_planner;
\c travel_planner
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 Key：

```env
# 数据库（根据实际修改密码）
DATABASE_URL=postgresql+asyncpg://travel_planner:your_password@localhost:5432/travel_planner

# LLM（DashScope 或 DeepSeek 二选一）
LLM_API_KEY=your_llm_api_key
LLM_PROVIDER=dashscope
LLM_MODEL=qwen-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 高德地图
AMAP_API_KEY=your_amap_web_service_key
VITE_AMAP_KEY=your_amap_js_api_key

# 安全
JWT_SECRET_KEY=generate_a_random_secret_here
```

> 切换 DeepSeek：在管理后台或 `.env` 中设置 `LLM_PROVIDER=deepseek`、`LLM_BASE_URL=https://api.deepseek.com/v1`、`LLM_MODEL=deepseek-v4-flash`

### 3. 安装依赖

```bash
# 后端
cd backend
uv sync

# 前端
cd ../frontend
npm install
```

### 4. 启动服务

```bash
# 后端（终端1）
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端（终端2）
cd frontend
npm run dev
```

### 5. 初始化管理员账户

```bash
cd backend
uv run python scripts/init_admin.py
```

默认创建 `admin` / `admin` 账户（拥有管理员权限）。自定义：

```bash
uv run python scripts/init_admin.py 用户名 密码
```

### 6. 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 管理后台 | http://localhost:5173/admin（用 admin 账户登录后访问） |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

## API 概览

### 认证

| 方法 | 端点 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 无 | 注册 |
| POST | `/api/v1/auth/login` | 无 | 登录，返回 JWT |

### Agent 对话（SSE 流式）

| 方法 | 端点 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/agent/chat` | 可选 | 发送消息，SSE 流式返回 |

### POI 搜索

| 方法 | 端点 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/poi/search` | 无 | 按城市/类别/关键词/评分搜索 |

### 行程管理

| 方法 | 端点 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/trips` | 需要 | 行程列表 |
| POST | `/api/v1/trips` | 需要 | 创建行程 |
| GET | `/api/v1/trips/{id}` | 需要 | 行程详情（含日程+POI） |
| PUT | `/api/v1/trips/{id}` | 需要 | 修改行程 |
| DELETE | `/api/v1/trips/{id}` | 需要 | 删除行程 |

### 会话管理

| 方法 | 端点 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/chat-sessions` | 需要 | 会话列表 |
| GET | `/api/v1/chat-sessions/{thread_id}` | 需要 | 会话详情 |
| PATCH | `/api/v1/chat-sessions/{thread_id}` | 需要 | 修改标题 |
| DELETE | `/api/v1/chat-sessions/{thread_id}` | 需要 | 删除会话 |

### 管理后台

| 方法 | 端点 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/admin/check` | Admin | 验证管理员 |
| GET/PUT | `/api/v1/admin/config` | Admin | 读取/更新配置 |
| GET | `/api/v1/admin/users` | Admin | 用户列表 |
| PATCH/DELETE | `/api/v1/admin/users/{id}` | Admin | 修改/删除用户 |
| GET | `/api/v1/admin/stats` | Admin | 数据统计 |
| GET/DELETE | `/api/v1/admin/trips/{id}` | Admin | 行程管理 |
| GET | `/api/v1/admin/pois` | Admin | POI 列表 |
| GET/DELETE | `/api/v1/admin/sessions/{id}` | Admin | 会话管理 |

## 使用流程

1. **注册/登录** — 右上角登录按钮
2. **发起规划** — 输入"帮我规划杭州三日游，喜欢历史文化"
3. **查看结果** — 右侧地图实时标注 POI + 绘制路线，左侧对话展示行程
4. **调整方案** — 继续对话调整（"第二天换一个博物馆"）
5. **地图选点** — 首页搜索 POI → 勾选感兴趣的点 → 发送规划请求
6. **管理后台** — 管理员账号访问 `/admin`，配置 LLM 和高德 Key

## 管理后台

侧边栏导航：模型配置 → 高德地图 → 用户管理 → 数据管理 → 数据库

- **模型配置**：切换 LLM 供应商（DashScope / DeepSeek）、选择模型、修改 API Key。**修改后立即生效，无需重启**
- **高德地图**：独立管理后端 AMAP_API_KEY 和前端 VITE_AMAP_KEY
- **用户管理**：查看所有用户、删除用户
- **数据管理**：统计面板 + 浏览行程/POI/会话

## SSE 事件类型

Agent 对话接口通过 SSE 推送以下 20 种事件类型：

| 类别 | 事件类型 |
|------|---------|
| 生命周期 | `thinking`, `text`, `done`, `error`, `progress` |
| 工具 | `tool_calling` |
| 地图 | `poi_result`, `route_result`, `candidates_ready` |
| 规划流水线 | `intent_detected`, `searching`, `scoring`, `clustering`, `day_routing`, `routing`, `day_routed`, `plan_summary` |
| 验证 | `critic_review`, `critic_result`, `validating` |

## 演示

参见 [docs/demo-script.md](docs/demo-script.md) 获取演示测试场景。

## 文档

- [可行性研究报告](docs/reports/01-可行性研究报告.md)
- [需求分析报告](docs/reports/02-需求分析报告.md)
- [概要设计报告](docs/reports/03-概要设计报告.md)
- [详细设计报告](docs/reports/04-详细设计报告.md)
- [数据库设计报告](docs/reports/05-数据库设计报告.md)
- [用户手册](docs/user-manual.md)

## 安全

- JWT 认证（HS256），可配置过期时间
- 密码 bcrypt 哈希存储
- API Key 通过环境变量管理，管理后台掩码显示
- 滑动窗口速率限制（Agent 20次/分钟，认证 10次/分钟）
- 配置白名单保护（仅允许更新安全的可热重载项）
- CORS 限制允许来源

## License

MIT
