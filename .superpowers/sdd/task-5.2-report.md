# Task 5.2: Pinia Stores — Report

**Status:** DONE
**Commit SHA:** `ba5330c`

## Files Created

### 1. `frontend/src/stores/map.ts`
- **State:** `pois: POI[]`, `routes: RouteData[]`, `selectedPOI: POI | null`, `center: MapCenter | null`, `zoom: number`
- **Actions:** `setPOIs(pois)`, `setRoutes(routes)`, `selectPOI(poi)`, `clearSelection()`, `clearMap()`, `setCenter(center)`, `setZoom(zoom)`
- **Getters:** `poiCount`, `hasSelection`
- Immutable updates via spread operator (no mutation)

### 2. `frontend/src/stores/trip.ts`
- **State:** `trips: Trip[]`, `currentTrip: Trip | null`, `loading: boolean`, `error: string | null`
- **Actions:** `fetchTrips()`, `fetchTrip(id)`, `createTrip(data)`, `updateTrip(id, data)`, `deleteTrip(id)`, `clearError()`
- **Getters:** `tripCount`
- Full CRUD with error handling — catches unknown errors, narrows to string messages, sets `loading` flag in `finally` blocks
- On create/delete: trips array is replaced immutably

### 3. `frontend/src/stores/chat.ts`
- **State:** `messages: ChatMessage[]`, `sessionId: string` (UUID via `crypto.randomUUID()`), `loading: boolean`, `error: string | null`
- **Actions:** `sendMessage(content)`, `clearMessages()`, `resetSession()`, `clearError()`
- **Getters:** `lastMessage`, `messageCount`
- **SSE handling inside `sendMessage`:**
  - `poi_result` → pushes POI data to map store (`mapStore.setPOIs`)
  - `route_result` → pushes route data to map store (`mapStore.setRoutes`)
  - `text` → accumulates into `assistantText`, added as a single assistant `ChatMessage` after stream completes
  - `error` → sets `error` state
  - `thinking`/`tool_calling`/`plan_summary` → acknowledged but no state mutation needed
- **Cross-store communication:** chat store imports and uses `useMapStore()` inside `handleEvent`

## Design Decisions

1. **Composition API (setup function) style** — all three stores use `defineStore(() => { ... })` pattern per requirements
2. **Immutable state updates** — arrays are always replaced via spread, never mutated
3. **Session persistence** — `sessionId` generated once with `crypto.randomUUID()` and persists for the store lifetime (no UUID dependency needed)
4. **Error handling** — all actions catch `unknown` errors, narrow safely to string messages, expose `error` state and `clearError()` action
5. **Type safety** — all public APIs explicitly typed; imported types from `@/types` and API functions from `@/api`
6. **No `console.log`** — no debug statements in production code

## Verification

- `vue-tsc --noEmit` passes with zero errors
