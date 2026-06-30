-- 0001_poi_indexes_and_constraints.down.sql
--
-- Reverses 0001_poi_indexes_and_constraints.sql.

DROP INDEX IF EXISTS ix_pois_description_trgm;
DROP INDEX IF EXISTS ix_pois_name_trgm;
-- pg_trgm is left in place — other tables / apps may rely on it.

DROP INDEX IF EXISTS uq_pois_extra_amap_id;
DROP INDEX IF EXISTS ix_pois_city_category_rating;
DROP INDEX IF EXISTS ix_pois_location_gist;