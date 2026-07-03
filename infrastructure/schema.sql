-- ============================================================
-- FixMyMedTech — Supabase Schema
-- ============================================================

-- Create the schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS fixmymedtech;
REVOKE ALL ON SCHEMA fixmymedtech FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA fixmymedtech FROM PUBLIC;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- ORGANIZATIONS (hospitals / health centres)
-- ============================================================
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

-- ============================================================
-- PROFILES (extends Supabase auth.users)
-- ============================================================
CREATE TABLE fixmymedtech.profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  organization_id UUID REFERENCES fixmymedtech.organizations(id),
  full_name       TEXT,
  role            TEXT CHECK (role IN ('admin', 'technician', 'clinical_staff', 'engineering_staff')) NOT NULL DEFAULT 'clinical_staff',
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- DEVICE CATEGORIES
-- ============================================================
CREATE TABLE fixmymedtech.device_categories (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,           -- e.g. "Ultrasound", "Ventilator"
  icon        TEXT DEFAULT '🏥'
);

INSERT INTO fixmymedtech.device_categories (name, icon) VALUES
  ('Ventilator', '🫁'),
  ('Ultrasound', '📡'),
  ('ECG Monitor', '💓'),
  ('Infusion Pump', '💉'),
  ('Oxygen Concentrator', '🫧'),
  ('Sterilizer', '🧪'),
  ('X-Ray', '🔬'),
  ('Defibrillator', '⚡'),
  ('Other', '🏥');

-- ============================================================
-- DEVICES (the core entity)
-- ============================================================
CREATE TABLE fixmymedtech.devices (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id   UUID NOT NULL REFERENCES fixmymedtech.organizations(id),
  organization_maintenance_id   UUID NOT NULL REFERENCES fixmymedtech.organizations(id),
  category_id       UUID REFERENCES fixmymedtech.device_categories(id),
  name              TEXT NOT NULL,
  manufacturer      TEXT,
  model             TEXT,
  serial_number     TEXT,
  manufacture_year  INT,
  acquisition_date  DATE,
  acquisition_type  TEXT CHECK (acquisition_type IN ('purchased', 'donated', 'leased')) DEFAULT 'purchased',
  location          TEXT,             -- e.g. "Ward 3 / Room 12"
  status            TEXT CHECK (status IN ('operational', 'maintenance', 'fault', 'decommissioned')) DEFAULT 'operational',
  last_maintenance  DATE,
  next_maintenance  DATE,
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- DOCUMENTS (manuals, guides, videos linked to devices)
-- ============================================================
CREATE TABLE fixmymedtech.documents (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id   UUID REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  category_id UUID REFERENCES fixmymedtech.device_categories(id),  -- can be generic (not device-specific)
  title       TEXT NOT NULL,
  type        TEXT CHECK (type IN ('manual', 'quick_guide', 'video', 'diagram', 'checklist')) NOT NULL,
  language    TEXT DEFAULT 'en',
  url         TEXT NOT NULL,           -- Supabase Storage URL
  size_kb     INT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MAINTENANCE LOGS
-- ============================================================
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

-- ============================================================
-- FAULT REPORTS (submitted by clinical staff via QR page)
-- ============================================================
CREATE TABLE fixmymedtech.fault_reports (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id       UUID NOT NULL REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  reported_by     UUID REFERENCES fixmymedtech.profiles(id),
  reporter_name   TEXT,               -- for anonymous reports (no account needed)
  reported_at     TIMESTAMPTZ DEFAULT NOW(),
  description     TEXT NOT NULL,
  severity        TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
  status          TEXT CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved')) DEFAULT 'open',
  resolved_at     TIMESTAMPTZ,
  resolution_notes TEXT
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE fixmymedtech.organizations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixmymedtech.profiles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixmymedtech.devices          ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixmymedtech.documents        ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixmymedtech.maintenance_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixmymedtech.fault_reports    ENABLE ROW LEVEL SECURITY;

-- Profiles: users see only their own
CREATE POLICY "profiles_own" ON fixmymedtech.profiles
  FOR ALL USING (auth.uid() = id);

-- Devices: users see only their organization's devices
CREATE POLICY "devices_org" ON fixmymedtech.devices
  FOR ALL USING (
    organization_id = (SELECT organization_id FROM fixmymedtech.profiles WHERE id = auth.uid())
  );

-- Same for maintenance logs and fault reports
CREATE POLICY "maintenance_org" ON fixmymedtech.maintenance_logs
  FOR ALL USING (
    device_id IN (
      SELECT id FROM fixmymedtech.devices WHERE organization_id = (
        SELECT organization_id FROM fixmymedtech.profiles WHERE id = auth.uid()
      )
    )
  );

CREATE POLICY "faults_org" ON fixmymedtech.fault_reports
  FOR ALL USING (
    device_id IN (
      SELECT id FROM fixmymedtech.devices WHERE organization_id = (
        SELECT organization_id FROM fixmymedtech.profiles WHERE id = auth.uid()
      )
    )
  );

-- Documents: readable by all authenticated users (manuals are public-ish)
CREATE POLICY "documents_read" ON fixmymedtech.documents
  FOR SELECT USING (true);

CREATE POLICY "documents_write" ON fixmymedtech.documents
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- ============================================================
-- TRIGGERS: updated_at
-- ============================================================
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

-- ============================================================
-- SEED: demo organization + devices
-- ============================================================
INSERT INTO fixmymedtech.organizations (id, name, country, region, type) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Mulago National Referral Hospital', 'Uganda', 'Kampala', 'hospital');

INSERT INTO fixmymedtech.devices (organization_id, organization_maintenance_id, name, manufacturer, model, serial_number, status, location, next_maintenance) VALUES
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Ventilator LTV 12', 'CareFusion', 'LTV 12', 'SN-0012', 'operational', 'ICU / Bed 4', NOW() + INTERVAL '30 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001','Ultrasound M-Turbo', 'SonoSite', 'M-Turbo', 'SN-00456', 'maintenance', 'Emergency / Bay 2', NOW() - INTERVAL '5 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001','ECG Monitor ProCare', 'GE Healthcare', 'ProCare B40', 'SN-00789', 'fault', 'Ward 3 / Room 7', NOW() - INTERVAL '15 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001','Infusion Pump Alaris', 'BD', 'Alaris GP', 'SN-01011', 'operational', 'Surgery / OR 1', NOW() + INTERVAL '60 days'),
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001','Oxygen Concentrator 5L', 'Invacare', 'Perfecto2', 'SN-01213', 'operational', 'Pediatrics / Room 2', NOW() + INTERVAL '14 days');