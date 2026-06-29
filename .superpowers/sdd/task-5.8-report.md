# Task 5.8: HomeView Assembly — Report

**Status:** DONE
**Commit:** 7385ba3

## What Was Implemented

### HomeView Split Layout
Replaced the placeholder `HomeView.vue` with a full split-layout view:

- **Left side (60%):** `MapView` component — full-height map display
- **Right side (40%):** `ChatPanel` component — chat interface

### Responsive Design
- Desktop: horizontal split (60/40)
- Mobile (<768px): vertical stack (50/50 map over chat)

### Global Styles Fix
Updated `style.css` to support full-height layout:
- `html, body` — `height: 100%; overflow: hidden`
- `#app` — `width: 100%; height: 100vh; overflow: hidden` (removed old template constraints like fixed 1126px width and centered text-align)

### App.vue
Verified — already uses `<router-view />` correctly. No changes needed.

## Files Modified
- `frontend/src/views/HomeView.vue` — replaced placeholder with split layout
- `frontend/src/style.css` — updated #app and html/body for full-height layout

## Design Decisions
- Used flexbox for the split layout (simple, no extra dependencies)
- `overflow: hidden` on all containers to prevent double scrollbars (Leaflet manages its own scroll)
- Mobile breakpoint at 768px with 50/50 split so both map and chat remain usable on small screens
- No router changes needed — route `/` → HomeView was already configured
