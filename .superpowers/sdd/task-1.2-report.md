# Task 1.2 Report: Database Models

**Status:** DONE

**Commits:** 96c4117 feat: database models - POI(PostGIS), Trip, User, ChatSession

**Test Results:** 36 passed in 0.40s

## Deliverables

### Files Created

1. **backend/app/database.py** (83 lines)
   - `async_engine` - SQLAlchemy 2.0 async engine with `pool_pre_ping=True`
   - `async_session_factory` - async session factory with `expire_on_commit=False`
   - `get_session()` - FastAPI dependency for session injection with commit/rollback

2. **backend/app/models/poi.py** (67 lines)
   - `Base` class - DeclarativeBase for all models
   - `POI` model - 14 columns including PostGIS GEOMETRY(POINT, 4326), ARRAY tags, JSONB extra_data
   - `to_dict()` method for serialization

3. **backend/app/models/user.py** (52 lines)
   - `User` model - 4 columns: id, username (unique), hashed_password, nickname
   - Relationships: chat_sessions, trips (cascade delete)

4. **backend/app/models/chat.py** (60 lines)
   - `ChatSession` model - 7 columns including JSONB messages and agent_state
   - Foreign key to users with CASCADE delete
   - Relationships: user

5. **backend/app/models/trip.py** (126 lines)
   - `Trip` model - 10 columns with date range and status tracking
   - `TripDay` model - 5 columns with day_number and date
   - `TripDayPOI` model - 8 columns for POI scheduling (sort_order, arrival/departure time, score)
   - All relationships use CASCADE delete with delete-orphan

6. **backend/app/models/__init__.py** (17 lines)
   - Exports all models and Base for clean imports

7. **backend/tests/test_models.py** (260 lines)
   - 36 tests covering all models
   - Tests: table names, columns, types, relationships, cascade deletes, foreign keys

### Test Coverage

- Base class inheritance: 2 tests
- POI model: 6 tests (columns, geometry type, ARRAY, JSONB, to_dict)
- User model: 4 tests (columns, unique constraint, relationships)
- ChatSession model: 6 tests (columns, JSONB fields, relationships, foreign keys)
- Trip model: 5 tests (columns, relationships, cascade deletes)
- TripDay model: 5 tests (columns, relationships, cascade deletes)
- TripDayPOI model: 5 tests (columns, relationships, foreign keys)
- Database module: 3 tests (engine, session factory, get_session)

### Technical Decisions

1. **Geometry Type**: Used `Geometry("POINT", srid=4326)` for PostGIS spatial queries
2. **JSON Storage**: JSONB for flexible extra_data and chat message storage
3. **Cascade Deletes**: All parent-child relationships use `cascade="all, delete-orphan"` with `ondelete="CASCADE"`
4. **Timestamps**: `server_default=func.now()` for created_at, `onupdate=func.now()` for updated_at
5. **Type Annotations**: Full type hints with `Mapped[]` and `mapped_column()` (SQLAlchemy 2.0 style)

### Architecture Notes

- All models inherit from shared `Base` (defined in poi.py)
- Circular imports avoided using `TYPE_CHECKING` blocks
- Async session pattern ready for FastAPI dependency injection
- PostGIS integration via GeoAlchemy2

## Verification

```bash
cd backend && uv run pytest tests/test_models.py -v
# Result: 36 passed in 0.40s

cd backend && uv run pytest tests/ -v
# Result: 37 passed in 0.39s (36 model tests + 1 health check)
```

## Next Steps

Task 1.2 complete. Ready for Task 1.3: Pydantic Schemas for API validation.
