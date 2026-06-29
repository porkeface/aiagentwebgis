# Task 4.4: Trip CRUD API

**Files:**
- Create: `backend/app/services/trip_service.py`
- Create: `backend/app/api/v1/trip.py`
- Test: `backend/tests/test_api/test_trip_api.py`

**Steps:**
1. trip_service.py: create_trip, get_trip, list_trips, update_trip, delete_trip
2. trip.py API: POST/GET/PUT/DELETE /api/v1/trips
3. All endpoints require JWT auth (dependency injection) - NOTE: JWT not yet implemented, use placeholder `get_current_user` dependency that returns a mock user_id for now. T4.5 will implement real JWT.
4. Write tests
5. Commit: `feat: Trip CRUD API with user ownership`
