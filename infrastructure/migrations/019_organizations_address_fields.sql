-- 019_organizations_address_fields.sql
-- Organizations no longer store geolocation: the healthsites.io import brings
-- country / region / address instead. Drops the lat/lng columns added by 018
-- and adds the address text column (country and region already exist).
-- Idempotent: safe whether or not 018 has been applied.

ALTER TABLE fixmymedtech.organizations
  DROP COLUMN IF EXISTS latitude,
  DROP COLUMN IF EXISTS longitude,
  ADD COLUMN IF NOT EXISTS address     TEXT;