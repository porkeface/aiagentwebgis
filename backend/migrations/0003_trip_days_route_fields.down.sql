-- 0003_trip_days_route_fields.down.sql
--
-- Reverse of 0003_trip_days_route_fields.sql — drops the route columns
-- the TripDay model declared. Used only for rolling back the migration
-- during development; production rollbacks should leave the data intact.

ALTER TABLE trip_days
    DROP COLUMN IF EXISTS polyline,
    DROP COLUMN IF EXISTS segments_json,
    DROP COLUMN IF EXISTS total_distance_km,
    DROP COLUMN IF EXISTS total_duration_min;