### Task 1.2: Database Models

**Files:**
- Create: `backend/app/database.py`, `backend/app/models/__init__.py`
- Create: `backend/app/models/poi.py` (POI with PostGIS GEOMETRY POINT)
- Create: `backend/app/models/trip.py` (Trip, TripDay, TripDayPOI)
- Create: `backend/app/models/user.py` (User)
- Create: `backend/app/models/chat.py` (ChatSession)
- Test: `backend/tests/test_models.py`

**Consumes:** config.py (DATABASE_URL)
**Produces:** 6 ORM models with spatial types, Base DeclarativeBase class

**Steps:**

1. Create `database.py` with async engine + session factory
2. Create POI model: id, name, category, city, location (Geometry POINT 4326), rating, tags (ARRAY), description, opening_hours, avg_visit_duration, review_count, extra_data, created_at. Include to_dict() method.
3. Create Trip/TripDay/TripDayPOI models with relationships and cascading deletes
4. Create User model: id, username (unique), hashed_password, nickname
5. Create ChatSession model: id, user_id, title, messages_json, agent_state_json
6. Create `models/__init__.py` exporting all models
7. Write tests verifying all model fields and relationships
8. Run: `pytest tests/test_models.py -v` -- all pass
9. Commit: `feat: database models - POI(PostGIS), Trip, User, ChatSession`

---