# Task 6.1: Seed Data

**Phase:** Integration  
**Files to Create:**
- `data/seed/seed_hangzhou.py`
- `data/seed/seed_chengdu.py`

**Consumes:** POI model (`backend/app/models/poi.py`), database config, PostGIS

**Produces:** Seed scripts that insert 20-30 POIs per city (Hangzhou, Chengdu) into PostGIS via SQLAlchemy

---

## Steps

1. Prepare 20-30 POIs per city with real coordinates
2. Script to insert into PostGIS via SQLAlchemy
3. Run seed script, verify POIs queryable
4. Commit: `feat: seed data for Hangzhou and Chengdu`

---

## POI Model Schema (from `backend/app/models/poi.py`)

```python
class POI(Base):
    __tablename__ = "pois"
    id: int (PK, autoincrement)
    name: str (String 255, not null, indexed)
    category: str (String 100, not null, indexed)
    city: str (String 100, not null, indexed)
    location: Geometry("POINT", srid=4326) (not null)
    rating: float (nullable)
    tags: list[str] (ARRAY of String, nullable)
    description: str (Text, nullable)
    opening_hours: str (String 255, nullable)
    avg_visit_duration: int (nullable)
    review_count: int (nullable)
    extra_data: dict (JSONB, nullable)
    created_at: datetime (server_default=now())
```

## Constraints

- PostGIS SRID: 4326 (WGS84)
- Use SQLAlchemy for DB insertion
- Cities: Hangzhou (杭州) and Chengdu (成都)
- POIs must have real geographic coordinates
- After seeding, POIs must be queryable via the existing POI model/API
