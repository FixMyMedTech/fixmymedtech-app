-- 020_device_healthsite.sql
-- Devices get an optional healthsite_id: the facility/site where the device is
-- physically located, distinct from organization_id (the responsible org) and
-- organization_maintenance_id (the org that maintains it).
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.devices
  ADD COLUMN IF NOT EXISTS healthsite_id UUID REFERENCES fixmymedtech.organizations(id);