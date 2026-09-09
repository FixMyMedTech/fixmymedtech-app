-- 006_maintenance_log_status.sql
-- Track the status of a maintenance log: open, in_progress or closed.

ALTER TABLE fixmymedtech.maintenance_logs
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open'
  CHECK (status IN ('open', 'in_progress', 'closed'));
