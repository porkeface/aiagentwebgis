# AI Travel Planner — 用户手册

## 1. 系统概述

AI Travel Planner 是一个基于人工智能的旅行规划系统，通过自然语言对话帮助用户完成行程规划。系统核心功能包括：

- **AI 对话规划**：与 AI 助手自然对话，自动推荐景点、美食、住宿，生成多日行程
- **地图可视化**：基于 Leaflet 的交互式地图，实时展示 POI 标记和路线
- **行程管理**：查看、编辑、删除已创建的行程，含每日时间线视图
- **POI 搜索**：按城市、分类、关键词、评分等条件搜索兴趣点

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Leaflet |
| 后端 | FastAPI + SQLAlchemy + LangGraph |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 |
| 缓存 | Redis 7 |
| AI | DashScope（通义千问） |
| 地图 | 高德地图 API |

## 3. 环境要求

- Docker & Docker Compose
- 高德地图 API Key（[申请地址](https://lbs.amap.com/)）
- DashScope API Key（[申请地址](https://dashscope.console.aliyun.com/)）

## 4. 启动系统

### 4.1 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入：

```env
# 数据库密码
DB_PASSWORD=your_secure_password

# 高德地图 API Key
AMAP_API_KEY=your_amap_key

# DashScope API Key（通义千问）
DASHSCOPE_API_KEY=your_dashscope_key

# JWT 密钥（建议生成随机字符串）
JWT_SECRET_KEY=your_random_jwt_secret
```

### 4.2 Docker Compose 一键启动

```bash
docker compose up -d
```

系统将启动 4 个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 数据库（PostGIS） |
| Redis | 6379 | 缓存 |
| Backend | 8000 | FastAPI 后端 |
| Frontend | 5173 | Vue 前端 |

### 4.3 验证启动

```bash
# 检查后端健康状态
curl http://localhost:8000/health
# 期望返回: {"status":"ok"}

# 查看 API 文档（Swagger UI）
open http://localhost:8000/docs

# 查看 API 文档（ReDoc）
open http://localhost:8000/redoc

# 访问前端
open http://localhost:5173
```

### 4.4 停止系统

```bash
docker compose down
```

如需清除数据：

```bash
docker compose down -v
```

## 5. 使用聊天界面

### 5.1 界面布局

系统主界面分为左右两栏：

- **左侧（60%）**：地图区域，展示 POI 标记和路线
- **右侧（40%）**：聊天面板，与 AI 助手对话

### 5.2 注册与登录

1. 在聊天面板上方找到登录/注册按钮
2. 输入用户名（≥3 字符）和密码（≥6 字符）
3. 注册成功后自动获取 JWT Token

### 5.3 开始对话

在聊天输入框中输入自然语言消息，AI 会：

1. 解析您的旅行意图
2. 调用工具搜索 POI（景点、美食等）
3. 根据偏好筛选和排序
4. 生成结构化行程计划
5. 在地图上标记 POI 和路线

**聊天过程中会看到以下事件类型：**

| 事件 | 含义 |
|------|------|
| 🤔 Thinking | AI 正在思考和分析 |
| 🔧 Tool Calling | AI 正在调用工具搜索数据 |
| 📍 POI Result | 搜索到的兴趣点结果 |
| 🗺️ Route Result | 路线规划数据 |
| 📋 Plan Summary | 行程计划摘要 |
| 💬 Text | AI 的文字回复 |
| ❌ Error | 错误提示 |

### 5.4 对话示例

```
你：帮我规划杭州3日游
AI：好的！我来为您规划杭州3日游...
    [搜索景点] [生成路线] [在地图上标注]
    Day 1：西湖 → 雷峰塔 → 灵隐寺
    Day 2：西溪湿地 → 宋城
    Day 3：龙井村 → 河坊街 → 钱塘江
```

## 6. 查看行程详情

### 6.1 行程列表

AI 生成行程后，可以通过聊天面板中的链接跳转到行程详情页。

### 6.2 行程详情页

行程详情页（`/trip/:id`）包含：

- **时间线视图**：按天展示每日安排，包含到达/离开时间
- **POI 卡片**：每个景点的名称、分类、评分、地址
- **地图联动**：点击 POI 可在地图上定位
- **路线展示**：各 POI 之间的推荐路线

### 6.3 操作

- 可以修改行程标题、状态、备注
- 可以删除行程（会同时删除关联的日程和 POI 数据）

## 7. POI 搜索

通过 API 直接搜索 POI：

```bash
# 搜索杭州景点
curl "http://localhost:8000/api/v1/poi/search?city=杭州&category=景点"

# 搜索成都美食，评分4.0以上
curl "http://localhost:8000/api/v1/poi/search?city=成都&category=美食&rating_min=4.0"

# 按关键词搜索
curl "http://localhost:8000/api/v1/poi/search?city=北京&keyword=故宫"

# 按区域搜索（bounding box: 经度min,纬度min,经度max,纬度max）
curl "http://localhost:8000/api/v1/poi/search?city=杭州&bbox=120.0,30.1,120.3,30.4"
```

## 8. API 文档

FastAPI 自动生成两种 API 文档：

- **Swagger UI**：`http://localhost:8000/docs` — 交互式 API 测试
- **ReDoc**：`http://localhost:8000/redoc` — 美观的 API 文档

所有 API 路径前缀为 `/api/v1/`。

## 9. 常见问题

### Q: 地图没有显示？

A: 检查 `AMAP_API_KEY` 是否正确配置，并确保前端代码中的地图服务配置正确。

### Q: AI 回复很慢？

A: AI 处理需要调用 DashScope 大模型，通常需要 5-30 秒。请耐心等待，聊天面板会显示 AI 正在思考的状态。

### Q: 如何修改数据库密码？

A: 修改 `.env` 中的 `DB_PASSWORD`，同时更新 `docker-compose.yml` 中的 `DATABASE_URL`，然后重启服务。

### Q: 如何重置所有数据？

A: 执行 `docker compose down -v` 清除数据卷，再重新启动。
