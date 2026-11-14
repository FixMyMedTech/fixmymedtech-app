-- 033_claims_and_tasks.sql — wave 5 (leaders and library)
--
-- achievement_claims: a member claims something the platform cannot see
-- (a QR tagging day, a repair helped by phone, a talk given) for one of the
-- "recognised" achievements. The team's lead (or a superuser) confirms it
-- alone; otherwise two members of that team confirm it. Confirming records
-- the achievement (achievement_records), which raises the star level.
--
-- community_tasks: a task board with points (find a missing manual, verify
-- a clinic, fill a brand list...). Someone takes a task, marks it done, and
-- the task's author or a team lead checks it; points count once checked.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS fixmymedtech.achievement_claims (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  achievement_key TEXT NOT NULL REFERENCES fixmymedtech.achievements(key),
  count           INTEGER NOT NULL DEFAULT 1,
  note            TEXT NOT NULL,
  proof_key       TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',
  confirmed_by    UUID[] NOT NULL DEFAULT '{}',
  reviewed_by     UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  reviewed_at     TIMESTAMPTZ,
  review_note     TEXT,
  record_id       UUID,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT achievement_claims_status_check
    CHECK (status IN ('pending', 'more_info', 'confirmed', 'declined')),
  CONSTRAINT achievement_claims_count_check CHECK (count BETWEEN 1 AND 100)
);
CREATE INDEX IF NOT EXISTS achievement_claims_status_idx ON fixmymedtech.achievement_claims (status);

CREATE TABLE IF NOT EXISTS fixmymedtech.community_tasks (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind             TEXT NOT NULL DEFAULT 'other',
  title            TEXT NOT NULL,
  details          TEXT,
  points           INTEGER NOT NULL DEFAULT 10,
  status           TEXT NOT NULL DEFAULT 'open',
  ref_manufacturer TEXT,
  ref_model        TEXT,
  ref_device_id    UUID REFERENCES fixmymedtech.devices(id) ON DELETE SET NULL,
  ref_org_id       UUID REFERENCES fixmymedtech.organizations(id) ON DELETE SET NULL,
  created_by       UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  taken_by         UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  taken_at         TIMESTAMPTZ,
  done_note        TEXT,
  done_at          TIMESTAMPTZ,
  checked_by       UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  checked_at       TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT community_tasks_kind_check
    CHECK (kind IN ('find_manual', 'verify_clinic', 'fill_brand_list', 'other')),
  CONSTRAINT community_tasks_status_check
    CHECK (status IN ('open', 'taken', 'review', 'done', 'cancelled')),
  CONSTRAINT community_tasks_points_check CHECK (points BETWEEN 1 AND 500)
);
CREATE INDEX IF NOT EXISTS community_tasks_status_idx ON fixmymedtech.community_tasks (status);
