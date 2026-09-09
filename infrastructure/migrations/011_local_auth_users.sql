-- 011_local_auth_users.sql
-- Replace Supabase-hosted auth (GoTrue / auth.users) with a local users table
-- managed entirely inside the fixmymedtech schema. Authlib issues + validates
-- JWTs against this table; no Supabase Auth dependency.

-- Local identity table. id is the PK shared 1:1 with profiles (and referenced
-- by all profile_id FKs). Password hashes are stored with bcrypt.
CREATE TABLE IF NOT EXISTS fixmymedtech.users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT,
  full_name     TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

DO $$
DECLARE
  dropped TEXT;
  rcount  INT;
BEGIN
  -- 1) Backfill a local user row for every existing profile so profiles.id
  --    can be FK'd to our users table. Legacy rows have no known credentials,
  --    so they get a placeholder email and no password (they can't log in, but
  --    their data is preserved).
  INSERT INTO fixmymedtech.users (id, email, full_name)
  SELECT p.id,
         'legacy-' || p.id || '@local',
         p.full_name
  FROM fixmymedtech.profiles p
  LEFT JOIN fixmymedtech.users u ON u.id = p.id
  WHERE u.id IS NULL
  ON CONFLICT (id) DO NOTHING;
  GET DIAGNOSTICS rcount = ROW_COUNT;

  -- 2) Drop any FK from profiles.id to Supabase's auth.users (name varies).
  FOR dropped IN
    SELECT c.conname
    FROM pg_constraint c
    JOIN pg_class     t  ON t.oid  = c.conrelid
    JOIN pg_namespace n  ON n.oid  = t.relnamespace
    JOIN pg_class     rt ON rt.oid = c.confrelid
    JOIN pg_namespace rn ON rn.oid = rt.relnamespace
    WHERE n.nspname = 'fixmymedtech'
      AND t.relname = 'profiles'
      AND rn.nspname = 'auth'
      AND rt.relname = 'users'
      AND c.contype = 'f'
  LOOP
    EXECUTE format('ALTER TABLE fixmymedtech.profiles DROP CONSTRAINT %I', dropped);
  END LOOP;

  -- 3) Add FK profiles.id -> fixmymedtech.users.id if not already present.
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_class     t  ON t.oid  = c.conrelid
    JOIN pg_namespace n  ON n.oid  = t.relnamespace
    JOIN pg_class     rt ON rt.oid = c.confrelid
    JOIN pg_namespace rn ON rn.oid = rt.relnamespace
    WHERE n.nspname = 'fixmymedtech'
      AND t.relname = 'profiles'
      AND rn.nspname = 'fixmymedtech'
      AND rt.relname = 'users'
      AND c.contype = 'f'
  ) THEN
    ALTER TABLE fixmymedtech.profiles
      ADD CONSTRAINT profiles_id_fkey
        FOREIGN KEY (id) REFERENCES fixmymedtech.users(id) ON DELETE CASCADE;
  END IF;
END $$;
