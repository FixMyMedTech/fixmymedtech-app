-- ============================================================
-- Migration 002: device_categories.slug + devices.category_id
-- The current model joins devices.category_id -> device_categories.slug.
-- Older DBs stored category_id as a UUID (device_categories.id) and had no slug.
-- ============================================================

-- 1. Add slug column
ALTER TABLE fixmymedtech.device_categories
  ADD COLUMN IF NOT EXISTS slug TEXT;

-- 2. Populate slugs from the category name
UPDATE fixmymedtech.device_categories
SET slug = lower(regexp_replace(trim(name), '[^a-zA-Z0-9]+', '_', 'g'))
WHERE slug IS NULL OR slug = '';

-- 3. De-duplicate slugs (suffix with a short hash) if any names collide
UPDATE fixmymedtech.device_categories a
SET slug = a.slug || '_' || left(md5(a.id::text), 6)
FROM fixmymedtech.device_categories b
WHERE a.id <> b.id
  AND a.slug = b.slug
  AND a.ctid > b.ctid;

-- 4. Convert devices.category_id from UUID to TEXT
ALTER TABLE fixmymedtech.devices
  DROP CONSTRAINT IF EXISTS devices_category_id_fkey;

ALTER TABLE fixmymedtech.devices
  ALTER COLUMN category_id TYPE TEXT USING category_id::text;

-- 5. Rewrite UUID category_id values to the matching slug
UPDATE fixmymedtech.devices d
SET category_id = c.slug
FROM fixmymedtech.device_categories c
WHERE d.category_id IS NOT NULL
  AND c.id::text = d.category_id;

-- 6. Null out leftover values that don't map to a slug (so the FK can be added)
UPDATE fixmymedtech.devices
SET category_id = NULL
WHERE category_id IS NOT NULL
  AND category_id NOT IN (SELECT slug FROM fixmymedtech.device_categories);

-- 7. Enforce slug uniqueness and not-null
ALTER TABLE fixmymedtech.device_categories
  ALTER COLUMN slug SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'device_categories_slug_key'
          AND conrelid = 'fixmymedtech.device_categories'::regclass
    ) THEN
        ALTER TABLE fixmymedtech.device_categories
            ADD CONSTRAINT device_categories_slug_key UNIQUE (slug);
    END IF;
END $$;

-- 8. Re-add FK devices.category_id -> device_categories(slug)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'devices_category_id_fkey'
          AND conrelid = 'fixmymedtech.devices'::regclass
    ) THEN
        ALTER TABLE fixmymedtech.devices
            ADD CONSTRAINT devices_category_id_fkey
            FOREIGN KEY (category_id) REFERENCES fixmymedtech.device_categories(slug);
    END IF;
END $$;
