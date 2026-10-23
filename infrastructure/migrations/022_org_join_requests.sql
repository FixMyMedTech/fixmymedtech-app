-- 022_org_join_requests.sql
-- Membership of an already-imported organization is self-declared, so it now
-- requires approval by an existing admin of that organization. Requests are
-- staged here until reviewed; only an approved request becomes an org_users row.
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS fixmymedtech.org_join_requests (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES fixmymedtech.organizations(id) ON DELETE CASCADE,
  profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  role            TEXT NOT NULL DEFAULT 'technician',
  status          TEXT NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reviewed_at     TIMESTAMPTZ,
  CONSTRAINT org_join_requests_role_check
    CHECK (role IN ('technician', 'clinical_staff', 'engineering_staff')),
  CONSTRAINT org_join_requests_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled'))
);

-- At most one open request per (org, user); approved/rejected rows are history.
CREATE UNIQUE INDEX IF NOT EXISTS uq_org_join_requests_open
  ON fixmymedtech.org_join_requests (organization_id, profile_id)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS ix_org_join_requests_review
  ON fixmymedtech.org_join_requests (organization_id, status);
