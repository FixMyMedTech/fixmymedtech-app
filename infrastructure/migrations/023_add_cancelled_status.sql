-- 023_add_cancelled_status.sql
-- Requesters can withdraw their own pending request from the groups page.
-- 'cancelled' is distinct from 'rejected': the requester withdrew it, an admin
-- did not turn it down. Both are terminal history rows and both free the
-- partial unique index, so the user may request again later.
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.org_join_requests
  DROP CONSTRAINT IF EXISTS org_join_requests_status_check;

ALTER TABLE fixmymedtech.org_join_requests
  ADD CONSTRAINT org_join_requests_status_check
  CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled'));
