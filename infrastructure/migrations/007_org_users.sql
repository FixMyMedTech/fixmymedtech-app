-- 007_org_users.sql
-- Create org_users junction table, migrate data, drop old profile columns,
-- and update RLS policies to use org_users.

-- 1. Create the junction table
CREATE TABLE IF NOT EXISTS fixmymedtech.org_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES fixmymedtech.organizations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'admin'
                    CHECK (role IN ('admin', 'technician', 'clinical_staff', 'engineering_staff')),
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (profile_id, organization_id)
);

-- 2. Migrate existing data from profiles → org_users
--    Only applies to legacy schemas that still have the old per-profile
--    organization_id/role columns (new bases already use org_users).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'fixmymedtech'
      AND table_name = 'profiles'
      AND column_name = 'organization_id'
  ) THEN
    INSERT INTO fixmymedtech.org_users (profile_id, organization_id, role)
    SELECT id, organization_id, role
    FROM fixmymedtech.profiles
    WHERE organization_id IS NOT NULL
    ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- 3. Drop old columns from profiles
ALTER TABLE fixmymedtech.profiles DROP COLUMN IF EXISTS role;
ALTER TABLE fixmymedtech.profiles DROP COLUMN IF EXISTS organization_id;

-- 4. Update RLS policies to use org_users

-- Drop old policies
DROP POLICY IF EXISTS "devices_org" ON fixmymedtech.devices;
DROP POLICY IF EXISTS "maintenance_org" ON fixmymedtech.maintenance_logs;
DROP POLICY IF EXISTS "faults_org" ON fixmymedtech.fault_reports;

-- Devices: user sees devices from any of their orgs (owned or maintained)
CREATE POLICY "devices_org" ON fixmymedtech.devices
  FOR ALL USING (
    organization_id IN (
      SELECT organization_id FROM fixmymedtech.org_users WHERE profile_id = auth.uid()
    )
    OR organization_maintenance_id IN (
      SELECT organization_id FROM fixmymedtech.org_users WHERE profile_id = auth.uid()
    )
  );

-- Maintenance logs: user sees logs on devices belonging to any of their orgs
CREATE POLICY "maintenance_org" ON fixmymedtech.maintenance_logs
  FOR ALL USING (
    device_id IN (
      SELECT id FROM fixmymedtech.devices WHERE
        organization_id IN (
          SELECT organization_id FROM fixmymedtech.org_users WHERE profile_id = auth.uid()
        )
        OR organization_maintenance_id IN (
          SELECT organization_id FROM fixmymedtech.org_users WHERE profile_id = auth.uid()
        )
    )
  );

-- Fault reports: same pattern
CREATE POLICY "faults_org" ON fixmymedtech.fault_reports
  FOR ALL USING (
    device_id IN (
      SELECT id FROM fixmymedtech.devices WHERE
        organization_id IN (
          SELECT organization_id FROM fixmymedtech.org_users WHERE profile_id = auth.uid()
        )
        OR organization_maintenance_id IN (
          SELECT organization_id FROM fixmymedtech.org_users WHERE profile_id = auth.uid()
        )
    )
  );

-- Enable RLS on org_users (admin-managed table)
ALTER TABLE fixmymedtech.org_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_users_own" ON fixmymedtech.org_users
  FOR ALL USING (profile_id = auth.uid());
