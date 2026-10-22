-- 024_fault_workflow.sql
-- Faults are resolved in steps, each step performed by a different person:
--   1. anyone reports it                                        -> status 'open'
--   2. the maintenance-org ADMIN assigns it to a member         -> 'assigned'
--   3. that assignee writes a diagnosis + online quote          -> 'diagnosed'
--   4. the healthsite ADMIN approves or rejects it              -> 'approved' / back to 'assigned'
--      (devices without a healthsite are approved by the maintenance-org admin)
--   5. the assignee repairs it and records the final price      -> 'resolved'
-- 'in_progress' stays available as an optional step the assignee can take
-- when they go on site.
--
-- Each step records WHO performed it, so the timeline can show the actor.
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.fault_reports
  ADD COLUMN IF NOT EXISTS assigned_by      UUID REFERENCES fixmymedtech.profiles(id),
  ADD COLUMN IF NOT EXISTS assigned_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS diagnosis        TEXT,
  ADD COLUMN IF NOT EXISTS diagnosed_by     UUID REFERENCES fixmymedtech.profiles(id),
  ADD COLUMN IF NOT EXISTS diagnosed_at     TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS quote_amount     NUMERIC(12, 2),
  ADD COLUMN IF NOT EXISTS quote_notes      TEXT,
  ADD COLUMN IF NOT EXISTS approval_status  TEXT,
  ADD COLUMN IF NOT EXISTS approved_by      UUID REFERENCES fixmymedtech.profiles(id),
  ADD COLUMN IF NOT EXISTS approved_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS approval_comment TEXT,
  ADD COLUMN IF NOT EXISTS final_price      NUMERIC(12, 2),
  ADD COLUMN IF NOT EXISTS resolved_by      UUID REFERENCES fixmymedtech.profiles(id);

ALTER TABLE fixmymedtech.fault_reports
  DROP CONSTRAINT IF EXISTS fault_reports_status_check;

ALTER TABLE fixmymedtech.fault_reports
  ADD CONSTRAINT fault_reports_status_check
  CHECK (status IN ('open', 'assigned', 'diagnosed', 'approved', 'in_progress', 'resolved'));

ALTER TABLE fixmymedtech.fault_reports
  DROP CONSTRAINT IF EXISTS fault_reports_approval_status_check;

ALTER TABLE fixmymedtech.fault_reports
  ADD CONSTRAINT fault_reports_approval_status_check
  CHECK (approval_status IS NULL OR approval_status IN ('pending', 'approved', 'rejected'));
