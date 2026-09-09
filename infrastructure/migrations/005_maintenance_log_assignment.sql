-- 005_maintenance_log_assignment.sql
-- Allow a maintenance log to be assigned to an engineer/technician of the
-- device's maintenance organization when it is started.

ALTER TABLE fixmymedtech.maintenance_logs
  ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES fixmymedtech.profiles(id);
