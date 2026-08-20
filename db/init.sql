-- ============================================================
-- FixMyMedTech — Local dev schema (mirrors Supabase without RLS)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Minimal auth.users mock for FK compatibility
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
  id      UUID PRIMARY KEY,
  email   TEXT
);

-- Main app schema
CREATE SCHEMA IF NOT EXISTS fixmymedtech;

CREATE TABLE fixmymedtech.organizations (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,
  country     TEXT NOT NULL,
  region      TEXT,
  type        TEXT CHECK (type IN ('hospital', 'clinic', 'health_centre', 'lab', 'engineering')) DEFAULT 'hospital',
  contact_email TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE fixmymedtech.profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username        TEXT NOT NULL UNIQUE,
  full_name       TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE fixmymedtech.org_users (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES fixmymedtech.organizations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL DEFAULT 'admin'
                  CHECK (role IN ('admin', 'technician', 'clinical_staff', 'engineering_staff')),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (profile_id, organization_id)
);

CREATE TABLE fixmymedtech.device_categories (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  icon        TEXT DEFAULT '🏥'
);

CREATE TABLE fixmymedtech.devices (
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

CREATE TABLE fixmymedtech.documents (
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

CREATE TABLE fixmymedtech.maintenance_logs (
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

CREATE TABLE fixmymedtech.fault_reports (
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

CREATE TRIGGER devices_updated_at
  BEFORE UPDATE ON fixmymedtech.devices
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER organizations_updated_at
  BEFORE UPDATE ON fixmymedtech.organizations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Seed categories
INSERT INTO fixmymedtech.device_categories (name, icon, slug) VALUES
  ('Ventilator', '🫁', 'ventilator'),
  ('Ultrasound', '📡', 'ultrasound_machine'),
  ('ECG Monitor', '💓', 'ecg_machine'),
  ('Infusion Pump', '💉', 'infusion_pump'),
  ('Oxygen Concentrator', '🫧', 'oxygen_concentrator'),
  ('Sterilizer', '🧪', 'autoclave_sterilizer'),
  ('X-Ray', '🔬', 'xray_machine'),
  ('Defibrillator', '⚡', 'defibrillator'),
  ('Anaesthetic Machine', '⛽', 'anaesthetic_machine'),
  ('Electronic Diagnostic Equipment', '🔍', 'electronic_diagnostic_equipment'),
  ('Electrosurgical Unit', '🔥', 'electrosurgical_unit'),
  ('Endoscope', '🔭', 'endoscope'),
  ('Incubator', '👶', 'infant_incubator'),
  ('Lamp', '💡', 'lamp'),
  ('Nebulizer', '🌫️', 'nebulizer'),
  ('Oxygen Cylinder / Flowmeter', '💨', 'oxygen_cylinder_flowmeter'),
  ('Pulse Oximeter', '🖐️', 'pulse_oximeter'),
  ('Scale', '⚖️', 'scale'),
  ('Sphygmomanometer', '🩸', 'sphygmomanometer'),
  ('Stethoscope', '🩺', 'stethoscope'),
  ('Suction Machine', '🌀', 'suction_machine'),
  ('Operating Table', '🛏️', 'operating_table'),
  ('Other', '🏥', 'other');

-- Seed org
INSERT INTO fixmymedtech.organizations (id, name, country, region, type) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Mulago National Referral Hospital', 'Uganda', 'Kampala', 'hospital');

-- Seed demo user (you'll create a real account via Supabase Auth, then insert your user ID here)
-- For demo: INSERT INTO auth.users (id, email) VALUES ('your-uuid-here', 'demo@hospital.org');
-- For demo: INSERT INTO fixmymedtech.profiles (id, full_name) VALUES ('your-uuid-here', 'Demo User');
-- For demo: INSERT INTO fixmymedtech.org_users (profile_id, organization_id, role) VALUES ('your-uuid-here', '00000000-0000-0000-0000-000000000001', 'admin');

-- Seed devices
INSERT INTO fixmymedtech.devices (organization_id, organization_maintenance_id, name, manufacturer, model, serial_number, status, location, next_maintenance) VALUES
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Ventilator LTV 12', 'CareFusion', 'LTV 12', 'SN-0012', 'operational', 'ICU / Bed 4', NOW() + INTERVAL '30 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Ultrasound M-Turbo', 'SonoSite', 'M-Turbo', 'SN-00456', 'maintenance', 'Emergency / Bay 2', NOW() - INTERVAL '5 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'ECG Monitor ProCare', 'GE Healthcare', 'ProCare B40', 'SN-00789', 'fault', 'Ward 3 / Room 7', NOW() - INTERVAL '15 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Infusion Pump Alaris', 'BD', 'Alaris GP', 'SN-01011', 'operational', 'Surgery / OR 1', NOW() + INTERVAL '60 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Oxygen Concentrator 5L', 'Invacare', 'Perfecto2', 'SN-01213', 'operational', 'Pediatrics / Room 2', NOW() + INTERVAL '14 days');
