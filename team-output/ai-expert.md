# AI Agent 系统架构设计

> **项目名称**：基于AI Agent的旅游路线智能规划与景点空间推荐系统  
> **角色**：AI/Agent 技术专家  
> **日期**：2026-06-29  

---

## 目录

1. [Agent 架构设计](#1-agent-架构设计)
2. [核心 Agent 能力设计](#2-核心-agent-能力设计)
3. [推荐算法设计](#3-推荐算法设计)
4. [Tool Use 设计](#4-tool-use-设计)
5. [空间知识图谱](#5-空间知识图谱)
6. [Prompt Engineering 方案](#6-prompt-engineering-方案)

---

## 1. Agent 架构设计

### 1.1 架构选型：多 Agent 协作（Orchestrator 模式）

**结论：推荐 Multi-Agent + Orchestrator 模式**，而非单 Agent。

| 维度 | 单 Agent | Multi-Agent（✅ 推荐） |
|------|----------|----------------------|
| 复杂度 | 低，但 prompt 臃肿 | 各 Agent 职责清晰，prompt 精简 |
| 空间推理 | 混在通用推理中，效果差 | 空间 Agent 专注地理计算 |
| 工具调用 | 工具集过大，模型选择困难 | 每个 Agent 挂载 3-5 个工具 |
| 可解释性 | 黑盒 | 每个 Agent 可独立追踪决策过程 |
| 课设答辩 | 缺乏亮点 | 多 Agent 协作流程是核心卖点 |
| 课程成绩 | 中等 | 显著加分 |

**为什么不用 ReAct 单 Agent？**

单 Agent ReAct 模式（Thought → Action → Observation 循环）虽然简单，但存在致命问题：
- **工具集膨胀**：10+ 个工具混在一起，LLM 频繁选错工具
- **上下文窗口压力**：空间计算的中间结果 + 对话历史 + 景点数据，轻松超过上下文限制
- **无法体现"Agent 系统"深度**：课设要求展示 Agent 的自主决策能力，单 Agent 太单薄

### 1.2 多 Agent 架构详细设计

```
                          ┌──────────────────────┐
                          │   Orchestrator Agent  │
                          │   (总控 / 路由器)      │
                          └──────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐
              │  意图理解   │  │  空间推荐   │  │  路线规划   │
              │   Agent     │  │   Agent    │  │   Agent    │
              └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
                    │                │                │
              ┌─────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐
              │  对话管理   │  │  知识图谱   │  │  地图渲染   │
              │   Agent     │  │  查询Agent  │  │   Agent    │
              └────────────┘  └────────────┘  └────────────┘
```

#### 各 Agent 角色定义

| Agent | 角色 | 能力边界 | 使用的 LLM |
|-------|------|---------|-----------|
| **Orchestrator** | 总控调度器 | 意图分类、Agent 路由、结果聚合、冲突仲裁 | Sonnet（需要强推理） |
| **IntentAgent** | 意图理解 | 从自然语言提取旅行偏好（预算/时间/兴趣/体力/人数） | Haiku（轻量快速） |
| **SpatialRecAgent** | 空间推荐 | 地理邻近性分析、空间聚类、区域主题识别、POI 推荐 | Sonnet（空间推理） |
| **RoutePlanAgent** | 路线规划 | TSP 变体求解、时空约束满足、路线优化 | Sonnet + 算法工具 |
| **DialogueAgent** | 对话管理 | 多轮上下文维护、状态追踪、槽位填充、澄清提问 | Haiku（高频低延迟） |
| **KGQueryAgent** | 知识图谱查询 | 景点关系查询、路径推理、主题聚类 | Haiku + 图查询工具 |
| **MapRenderAgent** | 地图渲染 | 将路线/推荐结果转为 GeoJSON、地图标注指令 | Haiku（格式化输出） |

#### 协作方式：Orchestrator 驱动的 Pipeline

```python
# Orchestrator 核心调度逻辑（伪代码）
class Orchestrator:
    def handle(self, user_message: str) -> str:
        # Step 1: 意图理解
        intent = self.intent_agent.parse(user_message)
        
        # Step 2: 路由决策
        if intent.type == "recommend":
            candidates = self.spatial_rec_agent.recommend(
                preferences=intent.preferences,
                context=self.dialogue_agent.get_context()
            )
            result = self.kg_query_agent.enrich(candidates)
            
        elif intent.type == "plan_route":
            pois = self.resolve_pois(intent.constraints)
            route = self.route_plan_agent.optimize(
                pois=pois,
                time_budget=intent.time_budget,
                transport=intent.transport_mode
            )
            result = self.map_render_agent.visualize(route)
            
        elif intent.type == "chat":
            result = self.dialogue_agent.respond(user_message)
        
        # Step 3: 结果聚合 + 回复生成
        return self.compose_response(result, intent)
```

### 1.3 Agent 记忆机制

```
┌─────────────────────────────────────────────────┐
│                 记忆系统架构                      │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐│
│  │  短期记忆    │  │  工作记忆    │  │ 长期记忆   ││
│  │ (Working)    │  │ (Session)    │  │ (Persistent)│
│  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘│
│         │                │               │       │
│  当前工具调用     本次会话的         用户画像 +     │
│  的中间结果       偏好槽位 +         历史路线 +     │
│  (Redis/内存)     对话摘要           推荐反馈      │
│                   (PostgreSQL)      (PostgreSQL +  │
│                                     向量数据库)    │
└─────────────────────────────────────────────────┘
```

| 记忆类型 | 存储内容 | 生命周期 | 实现方案 |
|---------|---------|---------|---------|
| **短期记忆** | 当前工具调用的中间结果、推理链 | 单次任务 | Python dict / Redis |
| **工作记忆** | 用户偏好槽位、已确认的约束、对话摘要 | 单次会话 | PostgreSQL session 表 |
| **长期记忆** | 用户画像、历史路线、偏好统计、推荐反馈 | 跨会话持久化 | PostgreSQL + pgvector |
| **共享记忆** | 景点知识库、空间索引、路线模板 | 全局只读 | PostGIS + 知识图谱 |

**Agent 间共享机制**：

```python
# Agent 间通过 SharedBlackboard 交换信息
class SharedBlackboard:
    """所有 Agent 共享的信息板"""
    
    def __init__(self):
        self.user_profile = {}      # 用户偏好（IntentAgent 写入）
        self.spatial_context = {}   # 空间上下文（SpatialRecAgent 写入）
        self.route_state = {}       # 路线状态（RoutePlanAgent 写入）
        self.tool_results = {}      # 工具调用结果（各 Agent 写入）
    
    def write(self, agent_id: str, key: str, value: Any):
        """Agent 写入信息（带来源标记）"""
        self.state[f"{agent_id}:{key}"] = {
            "value": value,
            "updated_by": agent_id,
            "timestamp": datetime.now()
        }
    
    def read(self, key: str) -> Any:
        """Agent 读取信息"""
        return self.state.get(key, {}).get("value")
```

---

## 2. 核心 Agent 能力设计

### 2.1 意图理解 Agent（IntentAgent）

#### 核心任务：从自然语言到结构化偏好

用户说："我下周六想带女朋友去西湖附近逛逛，预算 500 以内，不想走太多路，喜欢拍照和吃好吃的"

**提取结果**：

```json
{
  "intent_type": "recommend_and_plan",
  "temporal": {
    "date": "next_saturday",
    "duration_hours": null,  // 未明确，需要追问
    "time_budget": "full_day"
  },
  "social": {
    "companion": "girlfriend",
    "group_size": 2,
    "group_type": "couple"
  },
  "spatial": {
    "center": "西湖",
    "center_coords": [120.155, 30.255],
    "radius_km": 5.0
  },
  "preferences": {
    "interests": ["photography", "food", "scenic_walking"],
    "avoid": ["crowded", "commercial_traps"],
    "pace": "relaxed",  // 从"不想走太多路"推断
    "physical_level": "low"
  },
  "budget": {
    "total": 500,
    "currency": "CNY",
    "allocation": null  // 未细分
  },
  "missing_slots": ["duration_hours", "meal_preference", "transport_mode"]
}
```

#### 实现方案：LLM + 槽位提取 Prompt

```python
class IntentAgent:
    SYSTEM_PROMPT = """你是一个旅行意图解析专家。
    
你的任务是从用户的自然语言中提取结构化的旅行偏好。

你需要提取以下槽位（slot）：
- intent_type: recommend | plan_route | modify | chat | hybrid
- temporal: 时间相关（日期、时长、时段）
- social: 同行人员（人数、关系、特殊需求）
- spatial: 空间约束（起点、区域、半径）
- preferences: 兴趣偏好（活动类型、节奏、体力要求）
- budget: 预算约束（总额、分项）
- missing_slots: 未明确但对规划关键的信息

规则：
1. 推断合理默认值（如"不想走太多路" → physical_level: low）
2. 标注推断来源（inferred_from: "原文"）
3. 列出缺失但关键的信息（missing_slots）
4. 输出严格 JSON 格式
"""
    
    def parse(self, text: str) -> IntentResult:
        response = self.llm.chat(
            system=self.SYSTEM_PROMPT,
            user=text,
            response_format="json"
        )
        return IntentResult.from_json(response)
```

### 2.2 空间推荐 Agent（SpatialRecAgent）

#### 核心差异化：不是"推荐好吃的"，而是"推荐附近 500m 内评分 > 4.0 且适合拍照的餐厅"

**与纯语义推荐的区别**：

| 维度 | 纯语义推荐（ChatGPT 风格） | 空间感知推荐（本系统） |
|------|--------------------------|---------------------|
| 输入 | "推荐杭州好吃的" | 用户位置 + 半径 + 偏好 + 时间 |
| 距离 | 不考虑 | Haversine / 路网距离 |
| 聚集性 | 不考虑 | 空间聚类，避免推荐分散的点 |
| 可达性 | 不考虑 | 交通方式 + 实际通行时间 |
| 实时性 | 不考虑 | 拥挤度、天气、营业时间 |
| 输出 | 文本列表 | 带坐标、距离、方向的有序推荐 |

#### 空间推荐算法流程

```
用户请求 + 偏好
      │
      ▼
┌─────────────────────┐
│ Step 1: 空间过滤     │  ← PostGIS ST_DWithin 或 ST_MakeEnvelope
│ 筛选候选 POI        │     输出：候选集（通常 50-200 个）
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Step 2: 多因子评分   │  ← 见下方评分公式
│ 为每个候选打分       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Step 3: 空间多样性   │  ← MMR (Maximal Marginal Relevance)
│ 避免推荐扎堆的点     │     或空间约束下的 Top-K
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Step 4: 路线感知     │  ← 如果用户已有路线，优先推荐
│ 排序调整             │     路线沿途或终点附近的点
└──────────┬──────────┘
           │
           ▼
     Top-K 推荐结果
```

#### 多因子评分公式

```
Score(poi) = w1 × PreferenceMatch(poi, user_prefs)
           + w2 × SpatialProximity(poi, user_location)
           + w3 × TemporalFit(poi, current_time, duration)
           + w4 × Popularity(poi)
           + w5 × Novelty(poi, visited_history)
           - w6 × CrowdingPenalty(poi, current_time)
```

各因子定义：

```python
def preference_match(poi, prefs):
    """偏好匹配度：向量余弦相似度"""
    poi_tags = poi.embedding  # 景点标签的 embedding
    user_vec = prefs.embedding  # 用户偏好的 embedding
    return cosine_similarity(poi_tags, user_vec)

def spatial_proximity(poi, location, max_radius):
    """空间邻近度：距离越近分越高，超出半径为 0"""
    dist = haversine_distance(poi.coords, location)
    if dist > max_radius:
        return 0.0
    return 1.0 - (dist / max_radius)  # 线性衰减

def temporal_fit(poi, current_time, visit_duration):
    """时间适配度：营业时间、最佳游览时段"""
    if not poi.is_open(current_time):
        return 0.0
    if poi.peak_hours and current_time in poi.peak_hours:
        return 0.6  # 高峰期降低
    return 1.0

def crowding_penalty(poi, current_time):
    """拥挤惩罚：实时拥挤度"""
    crowd_level = get_realtime_crowding(poi.id, current_time)
    return crowd_level * 0.3  # 越拥挤扣分越多

# 推荐权重（可通过用户反馈动态调整）
DEFAULT_WEIGHTS = {
    "w1_pref": 0.30,
    "w2_spatial": 0.25,
    "w3_temporal": 0.15,
    "w4_popularity": 0.15,
    "w5_novelty": 0.10,
    "w6_crowd": 0.05
}
```

### 2.3 路线规划 Agent（RoutePlanAgent）

#### TSP 变体分析

本项目的路线规划不是标准 TSP，而是**带约束的 Orienteering Problem (OP)**：

| 特征 | 标准 TSP | 本项目变体 |
|------|---------|-----------|
| 目标 | 遍历所有点，总距离最短 | 在时间预算内，最大化体验价值 |
| 点数 | 必须全访问 | 可选子集（不一定全去） |
| 时间窗 | 无 | 景点有营业时间和最佳时段 |
| 预算 | 无 | 时间预算 + 金钱预算 |
| 交通 | 欧氏距离 | 路网距离 + 多种交通方式 |

#### 求解策略：分层方法

```
┌─────────────────────────────────────────┐
│         Route Planning Pipeline          │
├─────────────────────────────────────────┤
│                                           │
│  Layer 1: POI 选择（选哪些点去）         │
│  ┌─────────────────────────────────┐     │
│  │ 贪心 + 动态规划                  │     │
│  │ 输入：候选 POI + 时间预算        │     │
│  │ 目标：max Σ value(poi)          │     │
│  │ 约束：Σ time(poi) + travel ≤ T  │     │
│  └─────────────────────────────────┘     │
│           │                                │
│           ▼                                │
│  Layer 2: 顺序优化（去的顺序）            │
│  ┌─────────────────────────────────┐     │
│  │ 最近邻插入 + 2-opt 局部搜索      │     │
│  │ 输入：选定的 POI 子集            │     │
│  │ 目标：min 总旅行时间             │     │
│  │ 约束：时间窗（景点开放时间）      │     │
│  └─────────────────────────────────┘     │
│           │                                │
│           ▼                                │
│  Layer 3: 时间分配（每个点待多久）        │
│  ┌─────────────────────────────────┐     │
│  │ 按兴趣度分配游览时长              │     │
│  │ 高兴趣点 → 多给时间              │     │
│  │ 低兴趣点 → 打卡式短时间          │     │
│  └─────────────────────────────────┘     │
│                                           │
└─────────────────────────────────────────┘
```

#### 核心算法实现

```python
class RoutePlanAgent:
    
    def plan(self, pois: List[POI], constraints: RouteConstraints) -> Route:
        # Layer 1: POI 选择（贪心策略）
        selected = self._greedy_select(pois, constraints.time_budget)
        
        # Layer 2: 顺序优化
        route = self._nearest_neighbor(selected, constraints.start_point)
        route = self._two_opt_improve(route)
        
        # Layer 3: 时间窗约束检查 + 调整
        route = self._schedule_time_windows(route, constraints)
        
        # Layer 4: 时间分配
        route = self._allocate_durations(route, constraints.user_prefs)
        
        return route
    
    def _greedy_select(self, pois, time_budget):
        """贪心选择：按价值/时间比排序，逐个加入直到预算耗尽"""
        scored = []
        for poi in pois:
            value = poi.preference_score * poi.popularity_score
            time_cost = poi.avg_visit_duration  # 平均游览时间
            ratio = value / time_cost if time_cost > 0 else 0
            scored.append((poi, ratio))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        selected = []
        remaining_time = time_budget
        for poi, ratio in scored:
            if poi.avg_visit_duration <= remaining_time:
                selected.append(poi)
                remaining_time -= poi.avg_visit_duration
        
        return selected
    
    def _two_opt_improve(self, route: Route) -> Route:
        """2-opt 局部搜索：交换两条边，如果总距离减少则接受"""
        improved = True
        while improved:
            improved = False
            for i in range(1, len(route.stops) - 1):
                for j in range(i + 1, len(route.stops)):
                    new_route = route.reverse_segment(i, j)
                    if new_route.total_distance < route.total_distance:
                        route = new_route
                        improved = True
        return route
    
    def _schedule_time_windows(self, route, constraints):
        """时间窗调度：确保到达时景点开放"""
        current_time = constraints.start_time
        for stop in route.stops:
            # 如果到达太早，等待开门
            if current_time < stop.open_time:
                stop.wait_time = stop.open_time - current_time
                current_time = stop.open_time
            else:
                stop.wait_time = 0
            
            stop.arrival_time = current_time
            current_time += stop.visit_duration + stop.wait_time
            
            # 加入交通时间
            if stop.next_stop:
                travel = self.travel_time(stop, stop.next_stop, constraints.transport)
                current_time += travel
        
        return route
```

### 2.4 对话管理 Agent（DialogueAgent）

#### 多轮对话状态机

```
┌─────────────────────────────────────────────────┐
│              对话状态机（DFA）                     │
│                                                   │
│    ┌──────────┐  明确意图   ┌──────────────┐    │
│    │  INIT    │ ──────────→ │ PLAN_PHASE   │    │
│    │ (初始)    │             │ (规划阶段)    │    │
│    └────┬─────┘             └──┬───┬───┬───┘    │
│         │                      │   │   │         │
│    信息不足│    修改偏好 ────────┘   │   │         │
│         ▼                      │   │   │         │
│    ┌──────────┐  确认方案  ┌──▼───┐│ ┌─▼────────┐│
│    │ CLARIFY  │ ──────────→│EXECUTE││ │ MODIFY   ││
│    │ (追问)    │            │(执行) ││ │ (修改)    ││
│    └──────────┘            └──────┘│ └──────────┘│
│                                     │              │
└─────────────────────────────────────────────────┘
```

#### 对话状态追踪

```python
class DialogueState:
    """多轮对话的状态追踪"""
    
    def __init__(self):
        self.phase = "INIT"  # 当前阶段
        self.slots = {
            # 已填充的槽位
            "destination": None,
            "date": None,
            "duration": None,
            "budget": None,
            "interests": [],
            "companions": None,
            "start_location": None,
            "transport_mode": None,
        }
        self.confirmed = set()    # 已确认的槽位
        self.history = []         # 对话历史摘要
        self.current_plan = None  # 当前方案
    
    def update(self, new_info: dict):
        """更新槽位"""
        for key, value in new_info.items():
            if key in self.slots and value is not None:
                self.slots[key] = value
    
    def missing_critical_slots(self) -> List[str]:
        """返回缺失的关键槽位"""
        critical = ["destination", "date", "duration"]
        return [s for s in critical if self.slots[s] is None]
    
    def needs_clarification(self) -> bool:
        """是否需要追问"""
        return len(self.missing_critical_slots()) > 0
```

---

## 3. 推荐算法设计

### 3.1 推荐方案选型：混合方案（✅ 推荐）

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **知识图谱** | 可解释性强、关系推理 | 构建成本高、更新慢 | 景点间关系推理 |
| **向量检索** | 语义理解好、速度快 | 缺乏空间感知 | 偏好匹配 |
| **混合方案** | 兼具两者优点 | 架构稍复杂 | ✅ 本项目 |

**混合方案架构**：

```
用户自然语言输入
      │
      ├──→ Embedding Model ──→ 向量检索 ──→ 语义相似景点
      │                                      │
      ├──→ 意图解析 ──→ 空间查询 ──→ 空间候选景点
      │                                      │
      └──→ 知识图谱 ──→ 关系推理 ──→ 关联推荐景点
                                             │
                                             ▼
                                    ┌──────────────┐
                                    │ 多路融合排序  │
                                    │ (融合上面的    │
                                    │  三路结果)    │
                                    └──────────────┘
                                             │
                                             ▼
                                       最终推荐列表
```

### 3.2 空间感知推荐详细设计

#### 3.2.1 地理邻近性计算

```python
from geopy.distance import haversine

class SpatialCalculator:
    """空间计算工具集"""
    
    @staticmethod
    def nearby_pois(center: tuple, radius_km: float, poi_table: str) -> List[POI]:
        """
        空间邻近查询
        使用 PostGIS ST_DWithin（高效，走空间索引）
        """
        sql = f"""
        SELECT id, name, ST_X(geom) as lng, ST_Y(geom) as lat,
               ST_Distance(
                   geom::geography, 
                   ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
               ) as distance_m
        FROM {poi_table}
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
        ORDER BY distance_m ASC
        """
        return db.execute(sql, (center[1], center[0], center[1], center[0], radius_km * 1000))
    
    @staticmethod
    def road_network_distance(origin: tuple, destination: tuple, mode: str) -> float:
        """
        路网距离（非直线距离）
        实际使用 OSRM / OpenRouteService API
        """
        # 调用 OSRM API
        url = f"http://router.project-osrm.org/route/v1/{mode}/"
        url += f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        url += "?overview=false"
        
        response = requests.get(url).json()
        return response["routes"][0]["distance"]  # 米
    
    @staticmethod
    def travel_time_matrix(pois: List[POI], mode: str) -> np.ndarray:
        """
        旅行时间矩阵：计算所有 POI 两两之间的通行时间
        用于路线规划的距离矩阵输入
        """
        n = len(pois)
        matrix = np.zeros((n, n))
        
        # 批量调用 OSRM table API（比两两调用高效得多）
        coords = ";".join([f"{p.lng},{p.lat}" for p in pois])
        url = f"http://router.project-osrm.org/table/v1/{mode}/{coords}"
        
        response = requests.get(url).json()
        for i in range(n):
            for j in range(n):
                matrix[i][j] = response["durations"][i][j]  # 秒
        
        return matrix
```

#### 3.2.2 空间聚类：区域主题识别

```python
from sklearn.cluster import DBSCAN

class SpatialClusterer:
    """
    空间聚类：将 POI 按地理邻近性 + 主题相似性聚类
    用于发现"主题区域"（如：西湖北线-历史文化区、南山路-艺术区）
    """
    
    def cluster_pois(self, pois: List[POI], eps_km=0.5, min_samples=3):
        """
        DBSCAN 聚类
        eps: 邻域半径（km）
        min_samples: 最少点数
        """
        coords = np.array([[p.lat, p.lng] for p in pois])
        
        clustering = DBSCAN(
            eps=eps_km / 111.0,  # km → 度（近似）
            min_samples=min_samples,
            metric='haversine'
        ).fit(np.radians(coords))
        
        clusters = {}
        for i, label in enumerate(clustering.labels_):
            if label == -1:
                continue  # 噪声点
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(pois[i])
        
        return clusters
    
    def identify_cluster_theme(self, cluster: List[POI]) -> str:
        """
        识别聚类的主题
        通过统计聚类内 POI 的标签分布来推断
        """
        tag_counts = Counter()
        for poi in cluster:
            tag_counts.update(poi.tags)
        
        top_tags = tag_counts.most_common(3)
        return "、".join([t[0] for t in top_tags])
        # 例如："寺庙、园林、古迹" → 历史文化区
```

#### 3.2.3 多因子融合排序

```python
class HybridRanker:
    """多因子融合排序器"""
    
    def rank(self, candidates: List[POI], context: RecommendationContext) -> List[RankedPOI]:
        scored = []
        for poi in candidates:
            scores = {
                "preference": self._preference_score(poi, context.user_prefs),
                "spatial": self._spatial_score(poi, context),
                "temporal": self._temporal_score(poi, context),
                "popularity": self._popularity_score(poi),
                "novelty": self._novelty_score(poi, context.visited),
                "crowd_penalty": self._crowd_penalty(poi, context),
            }
            
            # 加权求和
            total = sum(
                context.weights.get(k, 0) * v 
                for k, v in scores.items()
            )
            
            scored.append(RankedPOI(
                poi=poi,
                total_score=total,
                score_breakdown=scores
            ))
        
        # 空间多样性重排（MMR）
        scored = self._mmr_rerank(scored, context, lambda_=0.7)
        
        return sorted(scored, key=lambda x: x.total_score, reverse=True)
    
    def _mmr_rerank(self, scored, context, lambda_=0.7):
        """
        Maximal Marginal Relevance
        在保证相关性的同时，增加推荐的空间多样性
        避免推荐 5 个紧挨着的同类型景点
        """
        if not scored:
            return scored
        
        selected = [scored[0]]
        remaining = scored[1:]
        
        while remaining and len(selected) < context.top_k:
            best_score = -1
            best_idx = 0
            
            for i, candidate in enumerate(remaining):
                # 相关性
                rel = candidate.total_score
                
                # 与已选集合的最大相似度
                max_sim = max(
                    self._similarity(candidate, s) 
                    for s in selected
                )
                
                # MMR 分数
                mmr = lambda_ * rel - (1 - lambda_) * max_sim
                
                if mmr > best_score:
                    best_score = mmr
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
```

### 3.3 向量检索方案

```python
from sentence_transformers import SentenceTransformer
import faiss

class VectorRetriever:
    """
    向量检索：用于语义级别的偏好-景点匹配
    """
    
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.index = None  # FAISS index
    
    def build_index(self, pois: List[POI]):
        """构建 FAISS 索引"""
        # 将景点信息拼接为文本
        texts = [
            f"{p.name} {p.category} {' '.join(p.tags)} {p.description}"
            for p in pois
        ]
        
        # 编码为向量
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        
        # 构建 FAISS 索引
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # 内积（余弦相似度）
        self.index.add(embeddings.astype('float32'))
        
        self.poi_map = {i: poi for i, poi in enumerate(pois)}
    
    def search(self, query: str, top_k: int = 20) -> List[POI]:
        """语义检索"""
        query_vec = self.model.encode([query], normalize_embeddings=True)
        distances, indices = self.index.search(query_vec, top_k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0:
                results.append((self.poi_map[idx], float(dist)))
        
        return results
```

---

## 4. Tool Use 设计

### 4.1 工具清单

Agent 系统需要以下工具（Tools），每个 Agent 挂载不同的工具子集：

| # | 工具名称 | 挂载 Agent | 用途 |
|---|---------|-----------|------|
| 1 | `spatial_search` | SpatialRecAgent | 空间范围搜索 POI |
| 2 | `route_optimize` | RoutePlanAgent | 路线优化（TSP 求解） |
| 3 | `travel_time_matrix` | RoutePlanAgent | 计算时间距离矩阵 |
| 4 | `weather_query` | SpatialRecAgent | 查询目的地天气 |
| 5 | `crowding_query` | SpatialRecAgent | 查询景点实时拥挤度 |
| 6 | `kg_query` | KGQueryAgent | 知识图谱查询 |
| 7 | `kg_reasoning` | KGQueryAgent | 知识图谱关系推理 |
| 8 | `embedding_search` | SpatialRecAgent | 向量语义检索 |
| 9 | `geo_encode` | SpatialRecAgent | 地名 → 坐标（地理编码） |
| 10 | `map_render` | MapRenderAgent | 生成地图可视化 GeoJSON |
| 11 | `budget_calc` | RoutePlanAgent | 预算计算与分配 |
| 12 | `poi_detail` | KGQueryAgent | 获取景点详细信息 |
| 13 | `user_history` | DialogueAgent | 查询用户历史偏好 |
| 14 | `realtime_info` | SpatialRecAgent | 查询实时信息（交通/活动） |

### 4.2 工具详细定义

#### Tool 1: spatial_search

```json
{
  "name": "spatial_search",
  "description": "在指定空间范围内搜索 POI（兴趣点），支持按类别、评分、标签过滤",
  "parameters": {
    "center": {
      "type": "array",
      "items": {"type": "number"},
      "description": "搜索中心坐标 [经度, 纬度]"
    },
    "radius_km": {
      "type": "number",
      "description": "搜索半径（公里）",
      "default": 5.0
    },
    "categories": {
      "type": "array",
      "items": {"type": "string"},
      "description": "POI 类别过滤，如 ['restaurant', 'scenic', 'museum']",
      "optional": true
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "标签过滤，如 ['适合拍照', '历史古迹']",
      "optional": true
    },
    "min_rating": {
      "type": "number",
      "description": "最低评分",
      "default": 0.0
    },
    "limit": {
      "type": "integer",
      "description": "返回数量上限",
      "default": 50
    }
  },
  "returns": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "id": "string",
        "name": "string",
        "coords": "[lng, lat]",
        "category": "string",
        "rating": "number",
        "tags": "array",
        "distance_m": "number",
        "avg_visit_duration_min": "number"
      }
    }
  }
}
```

#### Tool 2: route_optimize

```json
{
  "name": "route_optimize",
  "description": "对给定的 POI 集合进行路线顺序优化，最小化总旅行时间",
  "parameters": {
    "poi_ids": {
      "type": "array",
      "items": {"type": "string"},
      "description": "要访问的 POI ID 列表"
    },
    "start": {
      "type": "array",
      "items": {"type": "number"},
      "description": "起点坐标 [lng, lat]"
    },
    "end": {
      "type": "array",
      "items": {"type": "number"},
      "description": "终点坐标 [lng, lat]（可选，默认返回起点）",
      "optional": true
    },
    "transport_mode": {
      "type": "string",
      "enum": ["walking", "driving", "transit", "cycling"],
      "description": "交通方式",
      "default": "walking"
    },
    "time_windows": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "poi_id": "string",
          "open": "string (HH:MM)",
          "close": "string (HH:MM)"
        }
      },
      "description": "各 POI 的时间窗约束",
      "optional": true
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "optimized_order": "array of poi_ids",
      "total_distance_km": "number",
      "total_travel_time_min": "number",
      "segment_details": "array of {from, to, distance_km, travel_time_min}"
    }
  }
}
```

#### Tool 3: travel_time_matrix

```json
{
  "name": "travel_time_matrix",
  "description": "计算多个地点之间的两两旅行时间矩阵",
  "parameters": {
    "coords": {
      "type": "array",
      "items": {"type": "array", "items": {"type": "number"}},
      "description": "坐标列表 [[lng, lat], ...]"
    },
    "mode": {
      "type": "string",
      "enum": ["walking", "driving", "transit"],
      "default": "walking"
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "duration_matrix": "2D array (seconds)",
      "distance_matrix": "2D array (meters)"
    }
  }
}
```

#### Tool 4: weather_query

```json
{
  "name": "weather_query",
  "description": "查询指定位置未来几天的天气预报",
  "parameters": {
    "location": {
      "type": "array",
      "items": {"type": "number"},
      "description": "坐标 [lng, lat] 或地名"
    },
    "date_range": {
      "type": "object",
      "properties": {
        "start": "string (YYYY-MM-DD)",
        "end": "string (YYYY-MM-DD)"
      }
    }
  },
  "returns": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "date": "string",
        "temp_high": "number",
        "temp_low": "number",
        "condition": "string (晴/多云/雨/...)",
        "precipitation_prob": "number (0-1)",
        "outdoor_suitability": "number (0-1)"
      }
    }
  }
}
```

#### Tool 5: crowding_query

```json
{
  "name": "crowding_query",
  "description": "查询景点当前及预测的拥挤程度",
  "parameters": {
    "poi_ids": {
      "type": "array",
      "items": {"type": "string"},
      "description": "POI ID 列表"
    },
    "time_range": {
      "type": "object",
      "properties": {
        "start": "string (HH:MM)",
        "end": "string (HH:MM)",
        "date": "string (YYYY-MM-DD)"
      }
    }
  },
  "returns": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "poi_id": "string",
        "current_level": "string (低/中/高/极高)",
        "predicted_levels": "array by hour",
        "recommended_time": "string (建议到访时段)"
      }
    }
  }
}
```

#### Tool 6-7: kg_query / kg_reasoning

```json
{
  "name": "kg_query",
  "description": "查询知识图谱中的景点信息和关系",
  "parameters": {
    "query_type": {
      "type": "string",
      "enum": ["poi_info", "nearby_themes", "related_pois", "region_history"]
    },
    "poi_id": {"type": "string", "optional": true},
    "region": {"type": "string", "optional": true},
    "max_hops": {"type": "integer", "default": 2, "description": "关系推理跳数"}
  },
  "returns": {
    "type": "object",
    "description": "根据 query_type 返回不同结构"
  }
}
```

```json
{
  "name": "kg_reasoning",
  "description": "基于知识图谱进行关系推理，发现隐含的景点关联",
  "parameters": {
    "start_poi_id": {"type": "string"},
    "reasoning_type": {
      "type": "string",
      "enum": ["theme_chain", "historical_connection", "architectural_style", "cultural_context"]
    },
    "max_depth": {"type": "integer", "default": 3}
  },
  "returns": {
    "type": "object",
    "properties": {
      "reasoning_path": "array of {from, relation, to}",
      "recommended_pois": "array",
      "explanation": "string"
    }
  }
}
```

#### Tool 8: embedding_search

```json
{
  "name": "embedding_search",
  "description": "语义向量检索，根据自然语言描述找到最匹配的景点",
  "parameters": {
    "query": {"type": "string", "description": "自然语言查询"},
    "top_k": {"type": "integer", "default": 20},
    "spatial_filter": {
      "type": "object",
      "properties": {
        "center": "[lng, lat]",
        "radius_km": "number"
      },
      "optional": true
    }
  },
  "returns": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "poi_id": "string",
        "name": "string",
        "similarity_score": "number",
        "match_reason": "string"
      }
    }
  }
}
```

#### Tool 9: geo_encode

```json
{
  "name": "geo_encode",
  "description": "地理编码：将地名转换为经纬度坐标，或反向解析",
  "parameters": {
    "input": {"type": "string", "description": "地名或坐标"},
    "direction": {
      "type": "string",
      "enum": ["forward", "reverse"],
      "description": "forward=地名→坐标, reverse=坐标→地名"
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "name": "string",
      "coords": "[lng, lat]",
      "confidence": "number",
      "alternatives": "array"
    }
  }
}
```

#### Tool 10: map_render

```json
{
  "name": "map_render",
  "description": "将路线和推荐结果转换为地图可视化所需的 GeoJSON 数据",
  "parameters": {
    "route_data": {
      "type": "object",
      "properties": {
        "stops": "array of {poi_id, name, coords, arrival_time, duration}",
        "paths": "array of {from_coords, to_coords, mode}"
      }
    },
    "render_options": {
      "type": "object",
      "properties": {
        "show_timeline": "boolean",
        "show_distance_labels": "boolean",
        "highlight_theme": "string",
        "zoom_level": "number"
      }
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "geojson": "object (GeoJSON FeatureCollection)",
      "map_center": "[lng, lat]",
      "map_zoom": "number",
      "layer_config": "object"
    }
  }
}
```

#### Tool 11-14: 其他工具

```json
// Tool 11: budget_calc
{
  "name": "budget_calc",
  "parameters": {
    "poi_ids": "array",
    "budget_total": "number",
    "categories": "array (门票/餐饮/交通/购物)",
    "allocation_strategy": "string (均衡/侧重体验/节约)"
  },
  "returns": {
    "estimated_total": "number",
    "breakdown": "object {tickets, food, transport, shopping}",
    "within_budget": "boolean",
    "suggestions": "array of string"
  }
}

// Tool 12: poi_detail
{
  "name": "poi_detail",
  "parameters": {"poi_id": "string"},
  "returns": {
    "name": "string",
    "description": "string",
    "images": "array",
    "opening_hours": "object",
    "ticket_price": "number",
    "avg_visit_duration": "number",
    "tips": "string",
    "nearby_amenities": "array"
  }
}

// Tool 13: user_history
{
  "name": "user_history",
  "parameters": {
    "user_id": "string",
    "query_type": "string (visited_pois, preferences, past_routes)"
  },
  "returns": {"history_data": "object"}
}

// Tool 14: realtime_info
{
  "name": "realtime_info",
  "parameters": {
    "location": "[lng, lat]",
    "info_type": "string (traffic, events, closures)"
  },
  "returns": {"realtime_data": "object"}
}
```

### 4.3 工具调用链示例

#### 场景：用户说"帮我规划一条半天的西湖文化之旅"

```
Orchestrator
  │
  ├─→ IntentAgent.parse("帮我规划一条半天的西湖文化之旅")
  │     └─→ {destination: "西湖", duration: "半天", theme: "文化", 
  │           start: null, interests: ["文化", "历史"]}
  │
  ├─→ geo_encode("西湖")
  │     └─→ {coords: [120.155, 30.255]}
  │
  ├─→ SpatialRecAgent.recommend()
  │     ├─→ spatial_search(center=[120.155, 30.255], radius_km=5, 
  │     │     tags=["历史", "文化", "古迹", "博物馆"], limit=30)
  │     │     └─→ [灵隐寺, 岳庙, 六和塔, 龙井村, ...]
  │     ├─→ embedding_search("西湖文化之旅 历史古迹 人文景观")
  │     │     └─→ [苏堤, 白堤, 孤山, 雷峰塔, ...]
  │     ├─→ kg_reasoning(start_poi_id="灵隐寺", reasoning_type="theme_chain")
  │     │     └─→ {path: [灵隐寺 → 飞来峰 → 龙井 → 中国茶叶博物馆]}
  │     └─→ weather_query(location=[120.155, 30.255], date_range={...})
  │           └─→ {condition: "晴", outdoor_suitability: 0.9}
  │
  ├─→ RoutePlanAgent.plan()
  │     ├─→ travel_time_matrix(pois=[selected_6_pois], mode="walking")
  │     │     └─→ 6×6 时间矩阵
  │     ├─→ route_optimize(poi_ids=[...], start=[120.155, 30.255], 
  │     │     transport_mode="walking", time_windows=[...])
  │     │     └─→ {optimized_order: [...], total_distance: 4.2km, 
  │     │            total_travel_time: 85min}
  │     └─→ budget_calc(poi_ids=[...], budget_total=200)
  │           └─→ {estimated: 150, breakdown: {...}, within_budget: true}
  │
  └─→ MapRenderAgent.visualize()
        └─→ map_render(route_data={stops: [...], paths: [...]})
              └─→ {geojson: {...}, map_center: [...], map_zoom: 14}
```

---

## 5. 空间知识图谱

### 5.1 本体设计（Ontology）

```
┌─────────────────────────────────────────────────┐
│              知识图谱本体结构                      │
├─────────────────────────────────────────────────┤
│                                                   │
│  节点类型 (Node Types)                            │
│  ┌──────────────────────────────────────────┐   │
│  │ • Attraction（景点）                      │   │
│  │   属性: name, coords, category, rating,  │   │
│  │         tags, description, open_hours     │   │
│  │ • Region（区域）                          │   │
│  │   属性: name, boundary, theme, level     │   │
│  │ • Activity（活动）                        │   │
│  │   属性: name, duration, season, cost     │   │
│  │ • Theme（主题）                           │   │
│  │   属性: name, description                │   │
│  │ • Food（美食）                            │   │
│  │   属性: name, cuisine_type, price_range  │   │
│  │ • Transport（交通节点）                   │   │
│  │   属性: name, type, coords               │   │
│  │ • Event（事件/节庆）                     │   │
│  │   属性: name, date_range, location       │   │
│  └──────────────────────────────────────────┘   │
│                                                   │
│  关系类型 (Edge Types)                            │
│  ┌──────────────────────────────────────────┐   │
│  │ • NEAR（空间邻近）                        │   │
│  │   属性: distance_m, walk_time_min        │   │
│  │ • LOCATED_IN（位于）                      │   │
│  │   属性: region_name                       │   │
│  │ • BELONGS_TO_THEME（属于主题）            │   │
│  │   属性: relevance_score                   │   │
│  │ • CONNECTED_TO（路线连接）                │   │
│  │   属性: path_distance, transport_mode    │   │
│  │ • SIMILAR_TO（相似景点）                  │   │
│  │   属性: similarity_score, shared_tags    │   │
│  │ • FOOD_NEARBY（附近美食）                 │   │
│  │   属性: distance_m, rating               │   │
│  │ • HISTORICALLY_RELATED（历史关联）        │   │
│  │   属性: relation_desc, era               │   │
│  │ • SEASONAL_BEST（最佳季节）               │   │
│  │   属性: season, reason                   │   │
│  │ • ACCESSIBLE_FROM（可达性）               │   │
│  │   属性: transport, duration_min          │   │
│  └──────────────────────────────────────────┘   │
│                                                   │
└─────────────────────────────────────────────────┘
```

### 5.2 知识图谱构建

#### 数据来源

| 数据源 | 内容 | 获取方式 |
|--------|------|---------|
| OpenStreetMap | POI 坐标、类别、名称 | Overpass API |
| 携程/马蜂窝 | 景点描述、评分、攻略 | 爬虫 / API |
| 百度百科/Wiki | 景点历史、文化背景 | API |
| 高德地图 API | 交通、周边、实时数据 | API |
| 人工标注 | 主题标签、关系、路线模板 | 领域专家 |

#### 构建流程

```
原始数据
  │
  ▼
┌──────────────────────────┐
│ 1. 实体抽取（NER）        │  ← LLM 从文本中抽取景点/区域/活动实体
│    使用 LLM 做 NER        │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 2. 关系抽取（RE）         │  ← LLM 抽取实体间关系
│    "灵隐寺位于西湖区"      │     (景点, LOCATED_IN, 区域)
│    → (灵隐寺, located_in, │
│       西湖区)              │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 3. 空间关系计算           │  ← PostGIS 计算空间关系
│    ST_Distance → NEAR     │     NEAR, LOCATED_IN, ACCESSIBLE_FROM
│    ST_Contains → LOCATED_IN│
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 4. 主题聚类               │  ← 对景点按标签 + 位置聚类
│    → BELONGS_TO_THEME     │     发现"西湖十景"、"灵隐禅意"等主题
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 5. 图谱存储               │  ← Neo4j / NetworkX
│    节点 + 边 + 属性       │     支持 Cypher 查询
└──────────────────────────┘
```

### 5.3 Agent 如何查询和推理

```python
class KGQueryAgent:
    """知识图谱查询 Agent"""
    
    # 预定义的查询模板
    QUERIES = {
        # 查询景点附近的主题区域
        "nearby_themes": """
        MATCH (a:Attraction {id: $poi_id})-[:LOCATED_IN]->(r:Region)
        MATCH (other:Attraction)-[:LOCATED_IN]->(r)
        MATCH (other)-[:BELONGS_TO_THEME]->(t:Theme)
        WHERE a <> other
        RETURN t.name as theme, count(other) as poi_count
        ORDER BY poi_count DESC
        """,
        
        # 查找主题路线（基于主题链推理）
        "theme_chain": """
        MATCH path = (a:Attraction {id: $poi_id})
            -[:NEAR*1..3]->(b:Attraction)
        WHERE ALL(n IN nodes(path) 
            WHERE (n)-[:BELONGS_TO_THEME]->(:Theme {name: $theme}))
        RETURN [n IN nodes(path) | n.name] as chain,
               reduce(dist = 0, r IN relationships(path) | 
                   dist + r.distance_m) as total_distance
        ORDER BY total_distance ASC
        LIMIT 5
        """,
        
        # 查询景点的历史文化关联
        "historical_connection": """
        MATCH (a:Attraction {id: $poi_id})
            -[:HISTORICALLY_RELATED]->(b:Attraction)
        RETURN b.name as related_poi, 
               b.description as context,
               a.HISTORICALLY_RELATED.relation_desc as connection
        ORDER BY b.rating DESC
        """
    }
    
    def query(self, query_type: str, params: dict) -> dict:
        """执行图查询"""
        cypher = self.QUERIES[query_type]
        result = self.neo4j.run(cypher, **params)
        return result.data()
    
    def reason(self, start_poi: str, reasoning_type: str, max_depth: int = 3) -> dict:
        """
        多跳推理：Agent 自主决定推理路径
        例如：从灵隐寺出发，推理出"禅意文化路线"
        """
        # Step 1: 获取起点景点的主题
        themes = self.query("nearby_themes", {"poi_id": start_poi})
        
        # Step 2: 选择最相关的主题
        primary_theme = themes[0]["theme"] if themes else None
        
        # Step 3: 沿主题链推理
        if primary_theme:
            chains = self.query("theme_chain", {
                "poi_id": start_poi,
                "theme": primary_theme
            })
            
            return {
                "reasoning_path": chains,
                "primary_theme": primary_theme,
                "recommendation": f"基于{primary_theme}主题，推荐这条路线..."
            }
```

---

## 6. Prompt Engineering 方案

### 6.1 System Prompt 设计思路

#### 设计原则

1. **角色明确**：每个 Agent 的 System Prompt 必须清晰定义角色边界
2. **能力约束**：明确告知 Agent 能做什么、不能做什么
3. **工具说明**：清晰描述每个工具的用途和使用时机
4. **输出格式**：严格约束输出格式，便于下游处理
5. **空间感知注入**：通过 few-shot 示例教会 Agent 空间推理

#### Orchestrator System Prompt

```
你是一个旅游路线规划系统的总控 Agent。

你的职责：
1. 理解用户意图，将请求分发给合适的子 Agent
2. 协调各子 Agent 的输出，生成完整的旅行方案
3. 在多轮对话中维持上下文一致性

你可以调度的子 Agent：
- IntentAgent：解析用户意图，提取旅行偏好
- SpatialRecAgent：基于地理位置和空间关系推荐景点
- RoutePlanAgent：规划最优游览路线
- DialogueAgent：处理闲聊和追问
- KGQueryAgent：查询景点知识图谱
- MapRenderAgent：生成地图可视化数据

决策规则：
- 如果用户首次提出需求 → 先调 IntentAgent，再路由
- 如果用户要求推荐 → SpatialRecAgent + KGQueryAgent
- 如果用户要求规划路线 → RoutePlanAgent
- 如果用户修改已有方案 → 定位变更部分，增量更新
- 如果用户闲聊 → DialogueAgent

你必须：
- 在每次回复中说明你的决策过程（调了哪些 Agent，为什么）
- 当信息不足时，通过 DialogueAgent 追问关键信息
- 当多个 Agent 的结果冲突时，做出合理仲裁
```

#### SpatialRecAgent System Prompt（空间感知注入的关键）

```
你是一个专注于空间感知的旅游推荐 Agent。

核心能力：
你能够理解地理位置关系，进行空间推理，而不仅仅是语义匹配。

空间推理规则：
1. 距离优先：在满足偏好的前提下，优先推荐距离近的点
2. 聚集原则：推荐应该形成聚集区域，而非分散在各处
3. 主题区域：同一区域的景点往往共享主题特征
4. 可达性：考虑实际通行时间，而非直线距离
5. 路线连续性：推荐的点应该能形成合理的行走路线

当收到推荐请求时，你的思考过程应该是：
1. 确定搜索中心点和半径
2. 调用 spatial_search 获取候选集
3. 按多因子评分排序（偏好 + 距离 + 时间 + 人气）
4. 使用 MMR 保证空间多样性
5. 检查推荐结果是否形成合理的空间布局

示例：
用户说："我想在西湖边找个安静的地方喝茶拍照"
错误回答：推荐龙井村（好但太远，不符合"西湖边"）
正确回答：推荐孤山附近的茶馆（在西湖边 + 安静 + 适合拍照）
```

### 6.2 空间推理能力注入

#### Few-shot 示例策略

```
## 空间推理示例

### 示例 1：区域理解
用户："我在杭州东站，想去附近逛逛"
工具调用链：
  1. geo_encode("杭州东站") → [120.213, 30.290]
  2. spatial_search(center=[120.213, 30.290], radius_km=3)
推理：杭州东站附近 3km 内有城市阳台、钱江新城、万象城，
      以现代城市景观为主，适合城市漫步和购物

### 示例 2：路线连续性
用户："帮我规划从灵隐寺到断桥的步行路线"
工具调用链：
  1. route_optimize(pois=["灵隐寺", "断桥"], mode="walking")
  2. 中间经过：灵隐寺 → 飞来峰 → 北山路 → 断桥
推理：这条路线沿北山路步行，沿途有植物园、岳庙等景点，
      可以顺便参观，总步行距离约 3.5km

### 示例 3：时间-空间约束
用户："下午 2 点到 5 点，在西湖边能去哪？"
推理：
  - 时间预算：3 小时
  - 考虑交通时间，有效游览时间约 2-2.5 小时
  - 推荐 1-2 个景点（步行 15 分钟可达，游览 1-1.5 小时）
  - 需要考虑景点 5 点前是否关门
```

#### Chain-of-Thought（CoT）引导

```
当你需要推荐景点时，请按以下步骤思考：

[THINK] 
让我分析用户的需求：
- 空间约束：用户在 ___，搜索半径 ___
- 偏好匹配：用户对 ___ 感兴趣
- 时间约束：可用时间 ___

[SPATIAL]
空间分析：
- 以 ___ 为中心，___ km 范围内有 ___ 个候选景点
- 这些景点分布在 ___ 个区域
- 最佳游览区域是 ___，因为 ___

[RECOMMEND]
基于以上分析，我推荐：
1. ___ (距离 ___m，匹配原因：___)
2. ___ (距离 ___m，匹配原因：___)
3. ___ (距离 ___m，匹配原因：___)

这些推荐形成了 ___ 的游览动线。
```

### 6.3 多 Agent 协作 Prompt 模板

```
## Orchestrator 内部推理模板

[用户输入]: {user_message}

[步骤 1 - 意图分类]
→ 调用 IntentAgent
→ 结果: {intent_result}

[步骤 2 - 路由决策]
→ 基于意图，需要调用: {selected_agents}
→ 原因: {routing_reason}

[步骤 3 - 子 Agent 执行]
{for agent in selected_agents:}
  → 调用 {agent.name}
  → 输入: {agent_input}
  → 输出: {agent_output}

[步骤 4 - 结果聚合]
→ 整合各 Agent 输出
→ 冲突检测: {conflict_check}
→ 最终方案: {final_plan}

[步骤 5 - 回复生成]
→ 生成用户友好的回复
→ 包含: 推荐结果 + 路线 + 地图 + 预算
```

---

## 附录 A：技术选型建议

| 组件 | 推荐方案 | 备选方案 | 理由 |
|------|---------|---------|------|
| LLM（主模型） | Claude Sonnet | GPT-4o | 工具调用能力强，推理能力好 |
| LLM（轻量模型） | Claude Haiku | GPT-4o-mini | 高频调用场景（意图/对话） |
| Embedding | text-embedding-3-small | bge-m3 | 语义检索 |
| 向量数据库 | pgvector | Milvus | 与 PostGIS 同库，减少运维 |
| 空间数据库 | PostgreSQL + PostGIS | - | 空间查询标准方案 |
| 知识图谱 | Neo4j | NetworkX（小规模） | 图查询和推理 |
| 路线优化 | OSRM（自部署） | OpenRouteService API | 路网距离和路线 |
| 地图前端 | Mapbox GL JS | Leaflet | 渲染效果好，适合课设展示 |
| Agent 框架 | LangGraph | 自研 | 多 Agent 编排成熟方案 |
| 天气 API | OpenWeatherMap | 和风天气 | 免费额度够用 |

## 附录 B：评估指标

| 指标 | 定义 | 目标 |
|------|------|------|
| 意图解析准确率 | 正确提取所有关键槽位的比例 | > 85% |
| 推荐相关性 | 用户接受推荐的比例（Top-5 命中率） | > 60% |
| 路线合理性 | 路线总时间 ≤ 用户预算的比例 | > 90% |
| 空间合理性 | 推荐景点的平均空间紧凑度 | 聚类系数 > 0.7 |
| 响应时间 | 从用户输入到系统回复 | < 5s |
| 多轮成功率 | 3 轮内完成规划的比例 | > 80% |

## 附录 C：Agent 工具调用能力体现（课设核心卖点）

为了在答辩中体现 "Agent 自主决策" 而非 "简单 LLM 对话"，需要展示：

1. **工具选择能力**：Agent 根据情境自主选择正确的工具（不是硬编码）
2. **多步推理链**：展示 Agent 的 Thought → Action → Observation 链
3. **自适应行为**：当工具返回异常时，Agent 能调整策略
4. **冲突解决**：当多个约束矛盾时（如"要近 + 要好玩 + 要便宜"），Agent 能做出权衡
5. **空间推理**：Agent 不只是语义匹配，而是真的在做地理空间分析

建议在答辩 demo 中设计以下场景：

- 场景 1：用户模糊需求 → Agent 主动追问 → 空间推荐
- 场景 2：用户说"换一批" → Agent 理解上下文 → 排除已推荐 → 重新推荐
- 场景 3：时间不够 → Agent 自动精简路线 → 保留高价值景点
- 场景 4：天气突变 → Agent 主动建议室内替代方案
