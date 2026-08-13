-- 003_fault_assignment.sql
-- Add the assigned technician/engineer to fault reports so a fault can be
-- assigned to a member of the device's maintenance organization.

ALTER TABLE fixmymedtech.fault_reports
  ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES fixmymedtech.profiles(id);
