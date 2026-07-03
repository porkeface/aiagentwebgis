-- 0002_user_created_at.sql
--
-- Adds a created_at column to the users table so the admin user list and
-- audit queries can order by registration time. Backfills existing rows
-- with the current timestamp so the column is NOT NULL safe.
--
-- Apply:
--   psql "$DATABASE_URL" < migrations/0002_user_created_at.sql
--
-- Reverse with 0002_user_created_at.down.sql.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

UPDATE users
    SET created_at = NOW()
    WHERE created_at IS NULL;

ALTER TABLE users
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW();

CREATE INDEX IF NOT EXISTS ix_users_created_at
    ON users (created_at DESC);
