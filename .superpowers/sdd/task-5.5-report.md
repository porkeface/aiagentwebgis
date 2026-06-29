# Task 5.5 Report: Dialog-Map Linkage

**Status:** DONE  
**Commit:** b10a874  
**Date:** 2026-06-29

## What Was Done

### Critical Bug Fix: SSE Event Parsing

**Problem:** The backend sends all SSE events with `event: message\n` on the wire, wrapping the actual event type inside the JSON payload as `{ type: "<event_type>", data: {...} }`. The frontend's `parseSSEEvent()` was using the SSE event line ("message") as the type, which wasn't in the valid types list, causing ALL events to fall through to the default "text" handler.

**Impact:** `poi_result`, `route_result`, and `plan_summary` events were being treated as text updates — no map updates were happening.

**Solution:** Modified `parseSSEEvent()` in `frontend/src/api/agent.ts` to:
1. Detect if the parsed JSON has a `type` field (envelope format)
2. Extract the real event type from the envelope
3. Extract the inner `data` field from the envelope
4. Silently ignore non-envelope events (e.g., "done")

### SSE Event Handler Improvements

Updated `frontend/src/stores/chat.ts` to correctly extract data from the backend's event format:

#### poi_result Events
Backend sends: `{ pois: POI[], center: {lng, lat}, zoom?: number }`
- Calls `mapStore.setPOIs(pois)` with the POI array
- Calls `mapStore.setCenter(center)` with the calculated center
- Calls `mapStore.setZoom(zoom)` if provided
- MapView's `watch(pois)` automatically fits bounds

#### route_result Events
Backend sends: `{ daily_plans: DayPlan[], polylines: Polyline[] }`
- Calls `mapStore.setRoutes(daily_plans)` with the daily plans array
- Route visualization will be handled in T5.6

#### plan_summary Events
Backend sends: `{ city: string, days: number }`
- Calls `mapStore.setPlanSummary({ city, days })` to store trip metadata
- Available for UI components to display trip info

### Map Store Enhancements

Updated `frontend/src/stores/map.ts`:
- Added `PlanSummary` interface with `city` and `days` fields
- Added `planSummary` state ref
- Added `hasPlan` computed getter
- Added `setPlanSummary()` action
- Updated `clearMap()` to also reset `planSummary`

### Verified Components

#### MapView.vue
- ✅ Marker click handler correctly calls `mapStore.selectPOI(poi)`
- ✅ `watch(pois)` auto-fits map bounds when POIs update
- ✅ Uses computed properties for center and zoom from store

#### PoiMarker.vue
- ✅ Emits "select" event with POI data on marker click
- ✅ Displays POI popup with name, category, and rating

## Files Modified

1. `frontend/src/api/agent.ts` - Fixed SSE event parsing to unwrap JSON envelope
2. `frontend/src/stores/chat.ts` - Updated SSE handlers to extract data from correct envelope structure
3. `frontend/src/stores/map.ts` - Added planSummary state and setPlanSummary action

## Type Safety

All TypeScript type checks pass with no errors:
```bash
npx vue-tsc --noEmit  # No errors
```

## Data Flow

```
User Message
  ↓
Chat Store: sendMessage()
  ↓
Backend SSE Stream (event: message, data: {type, data})
  ↓
parseSSEEvent() extracts type and data from envelope
  ↓
handleEvent() dispatches by type:
  ├─ poi_result → mapStore.setPOIs() + setCenter()
  ├─ route_result → mapStore.setRoutes()
  ├─ plan_summary → mapStore.setPlanSummary()
  └─ text → accumulate for assistant message
  ↓
MapView watches mapStore.pois
  ↓
Auto-fits bounds to contain all POIs
  ↓
User clicks marker → mapStore.selectPOI()
```

## Testing Notes

The implementation is complete and type-safe. Manual testing requires:
- Backend running with LLM API keys configured
- Frontend dev server running
- User sending a message like "推荐南京3日游"

Expected behavior:
1. User sees "thinking" and "tool_calling" events in chat
2. POI markers appear on map
3. Map auto-zooms to fit all POIs
4. Trip summary card can be displayed (city + days)
5. Clicking a marker selects it and shows popup

## Next Steps

- **T5.6: Route Visualization** - Draw polylines between POIs for each day
- **T5.7: Trip Detail View** - Display plan summary and day-by-day itinerary
- **T5.8: HomeView Assembly** - Integrate MapView and ChatPanel in main layout
