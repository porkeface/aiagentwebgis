# Task 5.7: Trip Detail View

## Overview

Build the trip detail view with timeline and day cards for displaying planned travel itineraries.

## Files to Create

- `frontend/src/components/trip/TripTimeline.vue`
- `frontend/src/components/trip/DayCard.vue`
- `frontend/src/views/TripDetailView.vue`

## Implementation Steps

1. **TripTimeline**: Vertical timeline with DayCards
   - Display multiple days in chronological order
   - Visual timeline connector between days
   - Smooth scrolling and navigation

2. **DayCard**: POI cards in order with time, distance, transport info
   - Show POIs for each day in visiting order
   - Display time estimates for each POI
   - Show distance and transport mode between POIs
   - Include POI details (name, category, rating, description)

3. **TripDetailView**: Full page with timeline + mini map
   - Responsive layout with timeline and map side-by-side
   - Interactive map showing daily routes
   - Click on POI card to highlight on map
   - Click on map marker to scroll to POI card

4. Commit: `feat: trip detail view with timeline and day cards`

## Dependencies

- Requires completed Task 5.2 (Pinia Stores) for trip data
- Requires completed Task 5.3 (MapView) for map integration
- Requires completed Task 5.6 (Route Visualization) for route display
- Uses types from Task 5.1 (Types + API Layer)

## Acceptance Criteria

- Timeline displays all days with POIs in correct order
- DayCard shows complete information (time, distance, transport)
- TripDetailView provides both timeline and map views
- Interactive linkage between timeline and map
- Responsive design for mobile devices
