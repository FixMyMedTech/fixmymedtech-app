-- 012_fastapi_users.sql
-- Align fixmymedtech.users with FastAPI-Users' expected schema.
--  * rename password_hash -> hashed_password (FastAPI-Users writes this attr)
--  * add is_active / is_superuser / is_verified booleans

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'fixmymedtech' AND table_name = 'users' AND column_name = 'password_hash'
  ) THEN
    ALTER TABLE fixmymedtech.users RENAME COLUMN password_hash TO hashed_password;
  END IF;
END
$$;

ALTER TABLE fixmymedtech.users
  ADD COLUMN IF NOT EXISTS is_active    BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE fixmymedtech.users
  ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE fixmymedtech.users
  ADD COLUMN IF NOT EXISTS is_verified  BOOLEAN NOT NULL DEFAULT FALSE;
