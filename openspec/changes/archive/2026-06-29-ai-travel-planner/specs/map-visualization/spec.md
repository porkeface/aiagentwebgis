# Capability: Map Visualization

## Overview

Leaflet-based map visualization with POI markers, route drawing, and bidirectional linkage with AI dialog panel.

## Map Layers

| Layer | Content | Trigger |
|-------|---------|---------|
| Base | Amap tile layer | Always visible |
| POI markers | Attractions with numbered icons | On `poi_result` SSE message |
| Route polylines | Colored lines connecting POIs in order | On `route_result` SSE message |
| Cluster highlights | Semi-transparent area overlays | Optional, on spatial analysis display |

## Dialog-Map Linkage

### Backend → Frontend (Agent output drives map)
- Receive `poi_result` → Auto-mark POIs on map with numbered markers
- Receive `route_result` → Auto-draw colored polylines for each day's route
- Receive `plan_summary` → Show trip overview card
- Map auto-zooms/centers to fit all markers

### Frontend → Backend (User map interaction triggers Agent)
- User clicks POI marker → Show info popup with details
- User drags marker to reorder → Send reorder request → Agent re-optimizes route
- User clicks "replace POI" → Agent searches nearby alternatives

## Route Visualization

- Each day has a distinct color (Day 1: blue, Day 2: green, Day 3: orange, ...)
- Markers are numbered (1, 2, 3...) within each day
- Polylines show direction arrows
- Distance and duration labels on each segment

## Acceptance Scenarios

1. Agent outputs poi_result with 10 POIs → 10 numbered markers appear on map, map auto-zooms to fit
2. Agent outputs route_result with 2 days → 2 colored polylines drawn, Day 1 blue with markers 1-5, Day 2 green with markers 1-5
3. User clicks marker 3 on Day 1 → Info popup shows POI name, rating, description, opening hours
4. User drags marker 5 to position 2 → Route re-calculated, polyline updated, new order displayed
