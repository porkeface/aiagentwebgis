# Task 5.1: Types + API Layer

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/agent.ts`, `poi.ts`, `trip.ts`, `auth.ts`

**Steps:**
1. types/index.ts: POI, Trip, DayPlan, ChatMessage, SSEEvent, ParsedIntent interfaces
2. api/agent.ts: sendChatMessage() using fetch + ReadableStream for SSE
3. api/poi.ts: searchPOIs()
4. api/trip.ts: CRUD functions
5. api/auth.ts: register(), login(), store token in localStorage
6. Commit: `feat: frontend types and API layer`
