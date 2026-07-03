-- 0002_user_created_at.down.sql
--
-- Reverse of 0002_user_created_at.sql — drops the created_at column
-- and its index.

DROP INDEX IF EXISTS ix_users_created_at;

ALTER TABLE users
    DROP COLUMN IF EXISTS created_at;
