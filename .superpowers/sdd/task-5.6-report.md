# Task 5.6 Report: Route Visualization

**Status:** DONE
**Commit:** 04bc823
**Date:** 2026-06-29

## What Was Done

### RouteLayer.vue Component

Created `frontend/src/components/map/RouteLayer.vue` — a Leaflet layer component that renders route polylines on the map when route data arrives from the backend via SSE `route_result` events.

#### Data Flow
1. Backend sends `route_result` SSE event with `{ daily_plans: DayPlan[], polylines: Polyline[] }`
2. Chat store (`chat.ts`) calls `mapStore.setRoutes(daily_plans)`
3. RouteLayer watches `mapStore.routes` and reactively renders polylines + markers

#### Per-Day Colored Polylines
- **Day 1**: Blue (`#1890ff`)
- **Day 2**: Green (`#52c41a`)
- **Day 3**: Orange (`#fa8c16`)
- **Day 4+**: Purple (`#a855f7`)

Each day's POIs are connected by an `LPolyline` with:
- Weight: 4px
- Opacity: 0.85
- Smooth factor: 1
- Tooltip showing "Day N · X.X km"

#### Numbered POI Stop Markers
Each POI along a route gets a numbered circle marker:
- 24px circle with day-specific color
- White number on colored background
- White border (2px)
- Shadow for depth
- Tooltip showing stop number, POI name, and category

#### Distance/Duration Segment Labels
Between consecutive POIs, a permanent tooltip label shows:
- Distance in km (from backend segment data)
- Estimated travel duration in minutes (calculated at 30 km/h average city speed)
- White pill-shaped background with subtle shadow

#### Edge Cases Handled
- Empty routes array → nothing rendered
- Single POI in a day → no polyline, only the numbered marker
- Two POIs → polyline + 2 markers + 1 segment label
- Day number > 4 → cycles to purple (last color in palette)

### MapView.vue Integration

Modified `frontend/src/components/map/MapView.vue`:
1. Imported `RouteLayer` component
2. Added `<RouteLayer />` inside `<l-map>` (rendered before `PoiMarker` children)
3. Added `routes` computed ref from map store
4. Added `watch(routes, ...)` watcher that auto-fits map bounds when route data changes
5. Added `fitBoundsFromRoutes()` helper that extracts all POI coordinates across all days and fits the map

## Data Structure Contract

The backend's `route_result` event sends `daily_plans` with this shape:

```typescript
interface DailyPlan {
  day: number
  pois: Array<{
    id: number
    name: string
    category: string
    lng: number
    lat: number
    rating: number
    day_order?: number
  }>
  total_distance_km: number
  segments: Array<{
    from_poi_id: number
    to_poi_id: number
    distance_km: number
  }>
}
```

This matches the output from `backend/recommendation/pipeline.py` and `backend/recommendation/tsp.py`.

## Files Modified

1. **Created** `frontend/src/components/map/RouteLayer.vue` — Route visualization layer component
2. **Modified** `frontend/src/components/map/MapView.vue` — Integrated RouteLayer + added route bounds fitting

## Type Safety

All TypeScript type checks pass with no errors:
```bash
npx vue-tsc --noEmit  # No errors
```

RouteLayer defines its own local interfaces (`DailyPlan`, `RoutePOI`, `RouteSegment`) that match the backend's data shape, since `mapStore.routes` is typed as `RouteData[]` (generic `{ [key: string]: unknown }`) for flexibility.

## Component Architecture

```
MapView.vue
  └─ <l-map>
       ├─ <l-tile-layer>         (Amap tiles)
       ├─ <RouteLayer />         ← NEW: polylines + stop markers + segment labels
       └─ <PoiMarker> × N       (POI markers from poi_result)
```

RouteLayer renders three layers of Leaflet elements:
1. **LPolyline** per day (connecting all POIs in order)
2. **LMarker** per POI stop (numbered circle markers)
3. **LMarker** per segment (permanent tooltip labels at midpoints)

All three layers are computed properties for optimal reactivity — they only recompute when `mapStore.routes` changes.

## Commit

```
feat: route visualization with per-day colored polylines
```
