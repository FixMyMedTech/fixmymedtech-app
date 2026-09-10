-- ============================================================
-- Migration 000: base schema bootstrap
--
-- Defines the initial fixmymedtech tables so a FRESH database
-- (e.g. a brand-new Supabase project) can be bootstrapped purely
-- by the migration runner. All statements are idempotent:
--   * on databases seeded from infrastructure/db/init.sql (local
--     compose) the tables already exist and this file is a no-op;
--   * on already-migrated databases it is skipped entirely after
--     the first run.
--
-- The demo org/devices and the auth.users mock are intentionally
-- NOT here — init.sql keeps those for local development only.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS fixmymedtech;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS fixmymedtech.organizations (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,
  country     TEXT NOT NULL,
  region      TEXT,
  type        TEXT CHECK (type IN ('hospital', 'clinic', 'health_centre', 'lab', 'engineering')) DEFAULT 'hospital',
  contact_email TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixmymedtech.profiles (
  id          UUID PRIMARY KEY,
  username    TEXT NOT NULL UNIQUE,
  full_name   TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixmymedtech.org_users (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES fixmymedtech.organizations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL DEFAULT 'admin'
                  CHECK (role IN ('admin', 'technician', 'clinical_staff', 'engineering_staff')),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (profile_id, organization_id)
);

CREATE TABLE IF NOT EXISTS fixmymedtech.device_categories (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  icon        TEXT DEFAULT '🏥'
);

CREATE TABLE IF NOT EXISTS fixmymedtech.devices (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id   UUID NOT NULL REFERENCES fixmymedtech.organizations(id),
  organization_maintenance_id   UUID NOT NULL REFERENCES fixmymedtech.organizations(id),
  category_id       TEXT REFERENCES fixmymedtech.device_categories(slug),
  name              TEXT NOT NULL,
  manufacturer      TEXT,
  model             TEXT,
  serial_number     TEXT,
  manufacture_year  INT,
  acquisition_date  DATE,
  acquisition_type  TEXT CHECK (acquisition_type IN ('purchased', 'donated', 'leased')) DEFAULT 'purchased',
  location          TEXT,
  latitude          DOUBLE PRECISION,
  longitude         DOUBLE PRECISION,
  status            TEXT CHECK (status IN ('operational', 'maintenance', 'fault', 'decommissioned')) DEFAULT 'operational',
  last_maintenance  DATE,
  next_maintenance  DATE,
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixmymedtech.documents (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id   UUID REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  category_id UUID REFERENCES fixmymedtech.device_categories(id),
  title       TEXT NOT NULL,
  type        TEXT CHECK (type IN ('manual', 'quick_guide', 'video', 'diagram', 'checklist')) NOT NULL,
  language    TEXT DEFAULT 'en',
  url         TEXT NOT NULL,
  size_kb     INT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixmymedtech.maintenance_logs (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id       UUID NOT NULL REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  performed_by    UUID REFERENCES fixmymedtech.profiles(id),
  performed_at    TIMESTAMPTZ DEFAULT NOW(),
  type            TEXT CHECK (type IN ('preventive', 'corrective', 'inspection')) NOT NULL,
  description     TEXT,
  parts_replaced  TEXT,
  cost_usd        NUMERIC(10,2),
  next_due        DATE
);

CREATE TABLE IF NOT EXISTS fixmymedtech.fault_reports (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id       UUID NOT NULL REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  reported_by     UUID REFERENCES fixmymedtech.profiles(id),
  reporter_name   TEXT,
  reported_at     TIMESTAMPTZ DEFAULT NOW(),
  description     TEXT NOT NULL,
  severity        TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
  status          TEXT CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved')) DEFAULT 'open',
  resolved_at     TIMESTAMPTZ,
  resolution_notes TEXT
);

-- Triggers
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'devices_updated_at' AND tgrelid = 'fixmymedtech.devices'::regclass) THEN
    CREATE TRIGGER devices_updated_at
      BEFORE UPDATE ON fixmymedtech.devices
      FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'organizations_updated_at' AND tgrelid = 'fixmymedtech.organizations'::regclass) THEN
    CREATE TRIGGER organizations_updated_at
      BEFORE UPDATE ON fixmymedtech.organizations
      FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;