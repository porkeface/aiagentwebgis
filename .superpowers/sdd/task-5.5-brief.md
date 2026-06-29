# Task 5.5: Dialog-Map Linkage

**Files:**
- Modify: `frontend/src/stores/chat.ts` (SSE event handlers)
- Modify: `frontend/src/stores/map.ts` (auto-update from events)

**Steps:**
1. On poi_result SSE: map store.setPOIs(), MapView auto-marks
2. On route_result SSE: map store.setRoutes(), RouteLayer auto-draws
3. On plan_summary: show trip card
4. User clicks marker -> show info popup
5. Commit: `feat: dialog-map linkage - SSE events drive map updates`
