# Task 5.3 Report: MapView Component

老大，Task 5.3 已完成！

## Status

**DONE** ✓

## Commit

- **SHA:** `b0a0eedb890f60a43aaee5ad6976e159cf5101d7`
- **Message:** `feat: MapView with Leaflet + Amap tiles and POI markers`

## Files Created

1. `frontend/src/components/map/MapView.vue`
2. `frontend/src/components/map/PoiMarker.vue`

## Implementation Summary

### MapView.vue

- Uses `<l-map>` from `@vue-leaflet/vue-leaflet`
- Amap tile layer with URL pattern: `https://webrd0{s}.is.autonavi.com/maptile?style=8&x={x}&y={y}&z={z}`
- Subdomains: `['1', '2', '3', '4']`
- Center/zoom from map store with fallback defaults (Beijing [39.9, 116.4], zoom 12)
- Renders `<PoiMarker>` for each POI in store
- Auto-fits bounds when POIs change (watches `pois` array with `deep: true`)
- Uses `L.latLngBounds` to calculate bounds from all POI coordinates
- Full width/height container with min-height 300px
- Leaflet CSS already imported in `main.ts`

### PoiMarker.vue

- Uses `<l-marker>` with lat/lng from POI
- Custom `divIcon` with numbered marker (index + 1)
- Click handler emits `select` event
- Popup displays POI name, category, and rating
- Styled marker: blue circle with number, rotated for teardrop effect

### Additional Changes

- Installed `@vue-leaflet/vue-leaflet@0.10.1` dependency
- Global CSS styles for marker icons and popups (outside Vue scoped styles since Leaflet renders to DOM directly)

## Technical Notes

- TypeScript compilation passes with zero errors
- Used `shallowRef` for Leaflet map instance (non-reactive)
- Used `computed` for derived values (center, zoom, marker icon)
- Bounds fitting includes padding [50, 50] and max zoom 15
- Handles empty POI array gracefully (skips fitBounds)
