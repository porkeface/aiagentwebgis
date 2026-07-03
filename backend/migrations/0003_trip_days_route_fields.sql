-- 0003_trip_days_route_fields.sql
--
-- Brings `trip_days` into parity with `app/models/trip.py` by adding the
-- route fields the model declares (`polyline`, `segments_json`,
-- `total_distance_km`, `total_duration_min`). Previous databases built
-- from an older initdb script were missing these columns, so
-- `GET /api/v1/trips/{id}` 500'd with `UndefinedColumnError` whenever a
-- caller tried to fetch a trip that had segments persisted.
--
-- Apply with:
--   docker exec -i travel_planner_db psql -U travel_planner -d travel_planner \
--     < migrations/0003_trip_days_route_fields.sql
--
-- Reverse with 0003_trip_days_route_fields.down.sql.

ALTER TABLE trip_days
    ADD COLUMN IF NOT EXISTS polyline          TEXT,
    ADD COLUMN IF NOT EXISTS segments_json     TEXT,
    ADD COLUMN IF NOT EXISTS total_distance_km DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS total_duration_min DOUBLE PRECISION;
