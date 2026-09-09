-- 008_add_username.sql
-- Add unique username to profiles, auto-generated from full_name.

-- 1. Add the column (nullable first, for migration)
ALTER TABLE fixmymedtech.profiles ADD COLUMN username TEXT;

-- 2. Generate usernames for existing profiles
--    Format: slugified full_name + random 4-digit suffix, e.g. "john.smith4827"
DO $$
DECLARE
  rec RECORD;
  slug TEXT;
  suffix TEXT;
  candidate TEXT;
BEGIN
  FOR rec IN SELECT id, full_name FROM fixmymedtech.profiles LOOP
    slug := lower(regexp_replace(coalesce(rec.full_name, 'user'), '[^a-zA-Z0-9]+', '.', 'g'));
    slug := regexp_replace(slug, '^\.+|\.+$', '', 'g');
    slug := regexp_replace(slug, '\.{2,}', '.', 'g');
    IF slug = '' THEN slug := 'user'; END IF;
    -- Try up to 20 times to find a unique slug
    FOR i IN 1..20 LOOP
      suffix := floor(random() * 9000 + 1000)::text;
      candidate := slug || suffix;
      IF NOT EXISTS (SELECT 1 FROM fixmymedtech.profiles WHERE username = candidate) THEN
        UPDATE fixmymedtech.profiles SET username = candidate WHERE id = rec.id;
        EXIT;
      END IF;
    END LOOP;
  END LOOP;
END $$;

-- 3. Now enforce NOT NULL + UNIQUE
ALTER TABLE fixmymedtech.profiles ALTER COLUMN username SET NOT NULL;
ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT uq_profiles_username UNIQUE (username);
