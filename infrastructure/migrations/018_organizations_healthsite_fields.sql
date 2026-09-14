-- 018_organizations_healthsite_fields.sql
-- Merge healthsites into the organizations table: each organization row IS a
-- facility/site. New columns hold the healthsites.io link (OSM id/type),
-- geolocation and the `source` that distinguishes sites created in the app
-- ('app') from those imported from healthsites.io ('healthsites.io').
-- The healthsites.io API key lives in the .env file (HEALTHSITES_API_KEY),
-- not per-org in the database.

ALTER TABLE fixmymedtech.organizations
  ADD COLUMN IF NOT EXISTS osm_id       TEXT,
  ADD COLUMN IF NOT EXISTS osm_type     TEXT,
  ADD COLUMN IF NOT EXISTS latitude     FLOAT,
  ADD COLUMN IF NOT EXISTS longitude    FLOAT,
  ADD COLUMN IF NOT EXISTS source       TEXT NOT NULL DEFAULT 'app';

-- Unique on OSM facility so imports don't duplicate global sites.
-- (Postgres allows multiple NULL osm_id rows, so app-created sites are unaffected.)
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_organizations_osm' AND conrelid = 'fixmymedtech.organizations'::regclass
  ) THEN
    ALTER TABLE fixmymedtech.organizations
      ADD CONSTRAINT uq_organizations_osm UNIQUE (osm_id, osm_type);
  END IF;
END $$;