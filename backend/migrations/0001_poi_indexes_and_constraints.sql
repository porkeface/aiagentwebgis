-- 0001_poi_indexes_and_constraints.sql
--
-- Adds production-critical indexes and a uniqueness constraint that the
-- ORM declares in POI.__table_args__. This file is the manual counterpart
-- to the model changes — run it on existing databases to bring them in
-- line. The Alembic migration we will add next time will execute this
-- exact same DDL via op.execute().
--
-- Apply against the travel_planner database:
--   psql "$DATABASE_URL" < migrations/0001_poi_indexes_and_constraints.sql
--
-- Reverse with 0001_poi_indexes_and_constraints.down.sql.

-- GIST spatial index on POI.location. Without this, ST_Within / ST_DWithin
-- fall back to a sequential scan once the table exceeds a few thousand rows.
CREATE INDEX IF NOT EXISTS ix_pois_location_gist
    ON pois USING GIST (location);

-- Composite index for the most common filter combo: city + category, ordered
-- by rating. Used by /api/v1/poi/search.
CREATE INDEX IF NOT EXISTS ix_pois_city_category_rating
    ON pois (city, category, rating);

-- Unique partial index on extra_data->>'amap_id' so two POI rows can't
-- claim the same Amap record (protects save_plan from concurrent races).
CREATE UNIQUE INDEX IF NOT EXISTS uq_pois_extra_amap_id
    ON pois ((extra_data->>'amap_id'))
    WHERE extra_data->>'amap_id' IS NOT NULL;

-- Trigram-friendly index on POI.name for ILIKE '%keyword%' queries.
-- Requires the pg_trgm extension; CREATE EXTENSION must be run as a superuser
-- once per database.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS ix_pois_name_trgm
    ON pois USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_pois_description_trgm
    ON pois USING GIN (description gin_trgm_ops)
    WHERE description IS NOT NULL;