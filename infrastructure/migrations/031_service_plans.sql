-- 031_service_plans.sql — wave 2 (clinic CMMS)
--
-- Service plans: each device category has a service interval in months; a
-- device can override it. When a maintenance log closes, the device's next
-- service date rolls forward by that interval (or to the log's next_due).
-- NULL everywhere means the platform default (6 months, utils/service.py).
--
-- maintenance_reminders records each reminder email sent, so a device gets
-- one "due soon" and one "overdue" email per due date, not one a day.
--
-- Privacy switches on a clinic: whether its devices appear on the profile of
-- the engineer who registered them, and whether its name is hidden there.
--
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.device_categories
  ADD COLUMN IF NOT EXISTS service_interval_months INTEGER;

ALTER TABLE fixmymedtech.devices
  ADD COLUMN IF NOT EXISTS service_interval_months INTEGER;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.device_categories ADD CONSTRAINT device_categories_interval_check
    CHECK (service_interval_months IS NULL OR service_interval_months BETWEEN 1 AND 60);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.devices ADD CONSTRAINT devices_interval_check
    CHECK (service_interval_months IS NULL OR service_interval_months BETWEEN 1 AND 60);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Starting intervals. Commonly used preventive-maintenance frequencies; the
-- community can tune them per category in /admin. Unlisted categories use
-- the 6-month default.
UPDATE fixmymedtech.device_categories c SET service_interval_months = v.months
FROM (VALUES
  ('ventilator', 6), ('anaesthetic_machine', 6), ('defibrillator', 6),
  ('infusion_pump', 6), ('infant_incubator', 6), ('electrosurgical_unit', 6),
  ('oxygen_concentrator', 3), ('autoclave_sterilizer', 3), ('suction_machine', 6),
  ('xray_machine', 12), ('ultrasound_machine', 12), ('ecg_machine', 12),
  ('endoscope', 12), ('electronic_diagnostic_equipment', 12),
  ('pulse_oximeter', 12), ('nebulizer', 12), ('oxygen_cylinder_flowmeter', 12),
  ('sphygmomanometer', 12), ('scale', 12), ('lamp', 12), ('operating_table', 12),
  ('stethoscope', 24)
) AS v(slug, months)
WHERE c.slug = v.slug AND c.service_interval_months IS NULL;

CREATE TABLE IF NOT EXISTS fixmymedtech.maintenance_reminders (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id  UUID NOT NULL REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  due_date   DATE NOT NULL,
  kind       TEXT NOT NULL,
  recipients INTEGER NOT NULL DEFAULT 0,
  sent_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT maintenance_reminders_kind_check CHECK (kind IN ('due_soon', 'overdue')),
  CONSTRAINT maintenance_reminders_once UNIQUE (device_id, due_date, kind)
);

ALTER TABLE fixmymedtech.organizations
  ADD COLUMN IF NOT EXISTS show_devices_on_profiles BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS hide_name_on_profiles    BOOLEAN NOT NULL DEFAULT FALSE;
