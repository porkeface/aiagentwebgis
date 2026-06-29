# AI Travel Planner — 演示脚本

> 本脚本包含 5 个测试场景，用于演示和验证系统核心功能。

## 前置条件

- 系统已通过 Docker Compose 启动（参考 [用户手册](./user-manual.md)）
- 已配置有效的 `DASHSCOPE_API_KEY` 和 `AMAP_API_KEY`
- 前端可访问：http://localhost:5173
- 后端健康检查通过：`curl http://localhost:8000/health`

---

## 测试 1：基础行程规划（"帮我规划杭州3日游"）

**目标**：验证 AI 能正确解析行程意图，调用 POI 搜索，生成多日行程。

**步骤**：

1. 打开 http://localhost:5173
2. 如未登录，先注册账号（用户名 ≥ 3 字符，密码 ≥ 6 字符）
3. 在聊天输入框输入：`帮我规划杭州3日游`
4. 按回车发送

**预期结果**：

- [ ] 聊天面板显示 "Thinking" 状态（AI 正在思考）
- [ ] 出现 "Tool Calling" 事件（AI 调用搜索工具）
- [ ] 收到 POI 搜索结果（景点列表）
- [ ] 收到 Route Result（路线数据）
- [ ] 收到 Plan Summary（行程摘要，包含 Day 1/2/3 安排）
- [ ] 地图自动缩放到杭州区域
- [ ] 地图上出现多个 POI 标记点
- [ ] 地图上显示各 POI 之间的路线
- [ ] 聊天面板出现行程链接，可跳转到行程详情页

**验证点**：

```bash
# 后端日志应显示 agent 调用链
docker logs travel_planner_backend --tail 50

# 数据库应有新行程记录
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/trips
```

---

## 测试 2：POI 搜索（"成都附近有什么好吃的"）

**目标**：验证自然语言能触发美食类 POI 搜索。

**步骤**：

1. 在聊天输入框输入：`成都附近有什么好吃的`
2. 按回车发送

**预期结果**：

- [ ] AI 识别出 "成都" 城市和 "美食" 分类
- [ ] 调用 POI 搜索工具，category 为美食相关
- [ ] 返回美食 POI 列表（名称、地址、评分）
- [ ] 地图上标记美食位置
- [ ] AI 给出美食推荐文字回复

**API 直接验证**：

```bash
# 等价 API 调用
curl "http://localhost:8000/api/v1/poi/search?city=成都&category=美食"
```

**预期响应**：

```json
{
  "success": true,
  "data": {
    "total": 15,
    "items": [
      {
        "id": 101,
        "name": "某某火锅店",
        "category": "美食",
        "address": "成都市锦江区...",
        "lng": 104.08,
        "lat": 30.65,
        "rating": 4.5,
        "tags": ["火锅", "川菜"]
      }
    ]
  }
}
```

---

## 测试 3：多轮对话（逐步细化偏好）

**目标**：验证 AI 能理解上下文，在多轮对话中逐步调整行程。

**步骤**：

**第 1 轮**：

```
用户：我想去北京玩两天
```

预期：AI 返回北京 2 日游初步规划。

**第 2 轮**：

```
用户：我更喜欢吃小吃，不要太多景点
```

预期：AI 调整行程，减少景点，增加小吃推荐。

**第 3 轮**：

```
用户：第一天下午改成自由活动时间
```

预期：AI 修改第一天的行程安排，保留上午景点，下午留空。

**验证清单**：

- [ ] 每轮对话 AI 都引用了前文上下文
- [ ] 第 2 轮后美食 POI 占比明显增加
- [ ] 第 3 轮后第一天下午无 POI 安排
- [ ] 地图标记随每轮对话动态更新
- [ ] 最终行程保存到数据库

---

## 测试 4：行程详情视图

**目标**：验证行程详情页能正确展示 AI 生成的行程。

**步骤**：

1. 完成测试 1（生成杭州 3 日游）
2. 点击聊天中的行程链接，或手动访问 `/trip/1`
3. 查看行程详情页

**预期结果**：

- [ ] 页面标题显示行程城市（杭州）
- [ ] 显示行程天数（3 天）
- [ ] 时间线视图按天展示（Day 1 / Day 2 / Day 3）
- [ ] 每天的 POI 卡片显示：
  - [ ] 景点名称
  - [ ] 分类标签
  - [ ] 评分
  - [ ] 地址
  - [ ] 到达/离开时间
- [ ] 地图显示所有 POI 标记
- [ ] 地图显示 POI 之间的路线
- [ ] 点击 POI 卡片，地图自动定位（Dialog-Map 联动）
- [ ] 点击地图标记，高亮对应 POI 卡片

**API 验证**：

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/trips/1
```

**预期响应结构**：

```json
{
  "success": true,
  "data": {
    "id": 1,
    "city": "杭州",
    "days": 3,
    "status": "planned",
    "created_at": "2026-06-29T10:00:00",
    "daily_plans": [
      {
        "day_number": 1,
        "date": "2026-06-30",
        "notes": "...",
        "pois": [
          {
            "poi_id": 1,
            "sort_order": 1,
            "arrival_time": "09:00",
            "departure_time": "12:00",
            "score": 4.8,
            "name": "西湖",
            "category": "景点",
            "lng": 120.15,
            "lat": 30.25,
            "rating": 4.9
          }
        ]
      }
    ]
  }
}
```

---

## 测试 5：错误处理（网络/服务故障）

**目标**：验证系统在异常情况下的友好降级。

### 场景 A：DashScope API 不可用

**步骤**：

1. 在 `.env` 中设置无效的 `DASHSCOPE_API_KEY=invalid_key`
2. 重启后端：`docker compose restart backend`
3. 在聊天中输入：`帮我规划上海一日游`

**预期结果**：

- [ ] 聊天面板显示用户友好的错误消息（如 "抱歉，AI 服务暂时不可用，请稍后重试"）
- [ ] 不会显示原始堆栈跟踪或技术错误
- [ ] 系统不会崩溃，可以继续发送新消息

### 场景 B：数据库连接失败

**步骤**：

1. 停止数据库：`docker compose stop postgres`
2. 尝试访问行程列表 API

**预期结果**：

```bash
curl http://localhost:8000/api/v1/trips
# 期望返回 500 错误，带友好错误消息
```

- [ ] 后端返回 500 状态码
- [ ] 响应体包含友好错误描述
- [ ] 恢复数据库后（`docker compose start postgres`），功能恢复正常

### 场景 C：无效认证

**步骤**：

1. 使用过期的 JWT Token 访问受保护端点

**预期结果**：

```bash
curl -H "Authorization: Bearer expired_token" http://localhost:8000/api/v1/trips
# 期望返回 401 Unauthorized
```

- [ ] 返回 401 状态码
- [ ] 前端提示用户重新登录

---

## 演示检查清单

| 编号 | 场景 | 通过 | 备注 |
|------|------|------|------|
| 1 | 基础行程规划 | ☐ | |
| 2 | POI 搜索 | ☐ | |
| 3 | 多轮对话 | ☐ | |
| 4 | 行程详情 | ☐ | |
| 5 | 错误处理 | ☐ | |

---

## 常见问题排查

| 问题 | 排查步骤 |
|------|----------|
| AI 无响应 | 检查 `DASHSCOPE_API_KEY`，查看后端日志 `docker logs travel_planner_backend` |
| 地图不显示 | 检查 `AMAP_API_KEY`，确认前端网络请求无 CORS 错误 |
| 数据库错误 | 确认 PostgreSQL 容器健康：`docker compose ps` |
| 前端白屏 | 检查浏览器控制台，确认后端 CORS 配置正确 |
| 登录失败 | 确认 JWT_SECRET_KEY 已配置，非默认值 |
