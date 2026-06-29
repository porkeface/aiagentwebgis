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
