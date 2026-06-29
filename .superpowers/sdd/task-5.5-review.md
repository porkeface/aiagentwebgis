# Task 5.5 Review: Dialog-Map Linkage

**Reviewer:** Claude (code-reviewer)  
**Date:** 2026-06-29  
**Commit:** b10a874  
**Verdict:** ✅ **Approved**

---

## Spec Compliance

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | On poi_result SSE: mapStore.setPOIs(), MapView auto-marks | ✅ | Parses `{ pois, center, zoom }` envelope, calls setPOIs/setCenter/setZoom. MapView `watch(pois)` auto-fits bounds. |
| 2 | On route_result SSE: mapStore.setRoutes() | ✅ | Parses `{ daily_plans }` envelope, calls setRoutes. RouteLayer rendering deferred to T5.6 (expected). |
| 3 | On plan_summary: show trip card | ✅ | Parses `{ city, days }` envelope, stores in mapStore.planSummary. UI rendering deferred to T5.7 (expected). |
| 4 | User clicks marker → show info popup | ✅ | PoiMarker emits `select` → MapView calls `mapStore.selectPOI(poi)`. LPopup shows name/category/rating. |
| 5 | Commit: `feat: dialog-map linkage - SSE events drive map updates` | ✅ | Commit message matches spec format. |

**Spec compliance: ✅ All 5 requirements met.**

---

## Code Quality Assessment

### SSE Envelope Parsing (agent.ts) — Correct

The critical bug fix is well-implemented:
- Correctly detects `{ type, data }` JSON envelope from backend
- Extracts real event type and inner data
- Falls back to SSE event line for non-envelope events
- Unknown types return `null` (silently ignored, e.g. "done")
- Good inline comment explaining the backend's wire format

### Cross-Store Communication (chat.ts → map.ts) — Correct

- `useMapStore()` is called inside the event handler callback — this is the standard Pinia pattern (returns cached instance after first call)
- Each SSE case has proper null/type guards before calling store methods
- Immutable state updates in map store (`[...newPOIs]`, `{ ...summary }`)

### Type Safety — Acceptable

- Uses `unknown` casts with runtime narrowing (correct pattern for SSE data)
- `SSEEventType` is properly typed as a string union
- No `any` in critical paths
- `RouteData` interface is intentionally open (`[key: string]: unknown`) — acceptable since T5.6 will define the concrete shape

### Existing Components Verified

- **MapView.vue**: `watch(pois)` correctly auto-fits bounds; `onPoiSelect` calls `mapStore.selectPOI()`; uses computed center/zoom from store
- **PoiMarker.vue**: Custom DivIcon with numbered markers; LPopup with name/category/rating; emits `select` with POI data

---

## Issues

### Minor

1. **Variable shadowing in agent.ts line 32**: `const message = ...` shadows the function parameter `message: string`. Not a bug (different scope), but confusing to read.
   ```typescript
   // line 6: parameter
   export async function sendChatMessage(message: string, ...)
   // line 32: shadows parameter
   const message = detail && typeof detail === "object" ...
   ```
   **Suggestion:** Rename to `errMessage` or `failMessage`.

2. **plan_summary partial data silently dropped**: If backend sends `{ city: "南京" }` without `days`, the condition `city !== undefined && days !== undefined` fails and nothing is stored. Consider logging a warning or storing partial data.
   - **Severity:** Low — backend should always send both fields, but a console warning would aid debugging.

### Low

3. **poi_result POI objects not validated**: `payload.pois as POI[]` trusts the backend structure. If a POI is missing `lng`/`lat`, MapView's `fitBounds` will produce `NaN` coordinates.
   - **Severity:** Low — backend is trusted, and this is consistent with the project's approach (no Zod schemas on frontend SSE parsing).

4. **`route_result` ignores `polylines` field**: Backend sends `{ daily_plans, polylines }` but only `daily_plans` is stored. This is intentional (T5.6 will handle polylines), but no comment in the code explains the omission.
   - **Severity:** Low — a `// polylines handled in T5.6` comment would clarify intent.

---

## Summary

**Task quality: Approved ✅**

The implementation correctly fixes the critical SSE parsing bug and wires up all three event types to the map store. Code is clean, well-structured, and type-safe. The 4 minor/low issues are non-blocking and can be addressed opportunistically or in follow-up tasks.

### Strengths
- Critical SSE envelope parsing bug correctly identified and fixed
- Good runtime validation with type guards before store calls
- Immutable state updates in map store
- Clean separation: chat store handles SSE dispatch, map store handles state
- Existing MapView/PoiMarker components properly integrated

### No Blocking Issues
No CRITICAL or HIGH severity issues found.
