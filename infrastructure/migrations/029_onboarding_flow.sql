-- 029_onboarding_flow.sql
-- Engineer and clinic onboarding (spec "Engineer and clinic onboarding flow",
-- agreed 2026-11-12).
--
-- An engineer can register devices for a clinic only when two things are
-- true: they finished their three welcome quests, and that clinic named them
-- a responsible engineer. The clinic's own admins can always register.
--
--   profiles.onboarding_status  applicant (doing the welcome quests) →
--                            active once they are done; staff for clinic
--                            staff added by an organization admin (no
--                            quests). Deliberately neutral: the user-facing
--                            name for "quests done" lives in i18n.py.
--   profiles.active_since    when the quests were all done.
--   profiles.account_kind    engineer | clinic. Clinic accounts have no
--                            quests; they set up their clinic instead.
--   profiles.city / bio      part of the "complete your profile" quest.
--   onboarding_quests        quests the app can't read elsewhere (the
--                            community talk, confirmed by a host). Same shape
--                            as member_quests in draft PR #29.
--   organizations.invited_by          the engineer who invited the clinic;
--                                     kept whatever the clinic answers.
--   organizations.push_to_healthsites a clinic created here that is not on
--                                     healthsites.io yet, to push later.
--   organizations.clinic_status       active | talk_pending. A clinic that
--                                     signed up without an invitation stays
--                                     talk_pending until the talk host
--                                     unlocks it; engineers can't register
--                                     devices for it before that.
--   responsible_engineers    clinic ↔ engineer, confirmed or "not now".
--   onboarding_invitations   an engineer inviting a clinic, or a clinic
--                            inviting an engineer, by email with a token.
--
-- Backfill: every profile that exists before this migration is active, its
-- quests done, every existing organization is active, and every existing
-- technician is a confirmed responsible engineer of their organization, so
-- nobody already on the platform loses a right they had.
--
-- Idempotent: safe to re-run.

-- ── Profiles ────────────────────────────────────────────────

ALTER TABLE fixmymedtech.profiles
  ADD COLUMN IF NOT EXISTS onboarding_status TEXT,
  ADD COLUMN IF NOT EXISTS active_since  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS account_kind  TEXT NOT NULL DEFAULT 'engineer',
  ADD COLUMN IF NOT EXISTS city          TEXT,
  ADD COLUMN IF NOT EXISTS bio           TEXT;

-- Everyone already here is an existing account: active, quests done.
UPDATE fixmymedtech.profiles
   SET onboarding_status = 'active',
       active_since  = COALESCE(active_since, created_at, NOW());

ALTER TABLE fixmymedtech.profiles
  ALTER COLUMN onboarding_status SET DEFAULT 'applicant',
  ALTER COLUMN onboarding_status SET NOT NULL;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT profiles_onboarding_status_check
    CHECK (onboarding_status IN ('applicant', 'active', 'staff'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT profiles_account_kind_check
    CHECK (account_kind IN ('engineer', 'clinic'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT profiles_bio_length
    CHECK (bio IS NULL OR length(bio) <= 500);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Quests ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.onboarding_quests (
  profile_id    UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  quest_key     TEXT NOT NULL,
  count         INT  NOT NULL DEFAULT 1,
  confirmed_by  UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (profile_id, quest_key)
);

-- Record the talk as attended for existing accounts (history only: their
-- onboarding_status already unlocks everything).
INSERT INTO fixmymedtech.onboarding_quests (profile_id, quest_key)
  SELECT id, 'community_talk' FROM fixmymedtech.profiles
  ON CONFLICT DO NOTHING;

-- ── Organizations ───────────────────────────────────────────

ALTER TABLE fixmymedtech.organizations
  ADD COLUMN IF NOT EXISTS invited_by           UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS push_to_healthsites  BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS clinic_status        TEXT NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS talk_confirmed_by    UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS talk_confirmed_at    TIMESTAMPTZ;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.organizations ADD CONSTRAINT organizations_clinic_status_check
    CHECK (clinic_status IN ('active', 'talk_pending'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Responsible engineers ───────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.responsible_engineers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES fixmymedtech.organizations(id) ON DELETE CASCADE,
  engineer_id     UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  status          TEXT NOT NULL DEFAULT 'confirmed',
  -- inviter: the engineer who invited the clinic; added: named by a clinic
  -- admin; backfill: technician before this migration.
  source          TEXT NOT NULL DEFAULT 'added',
  kind            TEXT,
  added_by        UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  confirmed_by    UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  confirmed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT responsible_engineers_status_check CHECK (status IN ('confirmed', 'not_now')),
  CONSTRAINT responsible_engineers_source_check CHECK (source IN ('inviter', 'added', 'backfill')),
  CONSTRAINT responsible_engineers_kind_check   CHECK (kind IS NULL OR kind IN ('internal', 'external')),
  CONSTRAINT uq_responsible_engineers UNIQUE (organization_id, engineer_id)
);
CREATE INDEX IF NOT EXISTS ix_responsible_engineers_engineer
  ON fixmymedtech.responsible_engineers (engineer_id);

-- Technicians could register devices for their organization before this
-- migration; keep that right.
INSERT INTO fixmymedtech.responsible_engineers
    (organization_id, engineer_id, status, source, kind, confirmed_at)
  SELECT organization_id, profile_id, 'confirmed', 'backfill', 'internal', NOW()
    FROM fixmymedtech.org_users
   WHERE role = 'technician'
  ON CONFLICT (organization_id, engineer_id) DO NOTHING;

-- ── Invitations ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.onboarding_invitations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- clinic: an engineer invites a clinic. engineer: a clinic invites an
  -- engineer to become one of its responsible engineers.
  kind            TEXT NOT NULL,
  email           TEXT NOT NULL,
  message         TEXT,
  token           TEXT NOT NULL UNIQUE,
  invited_by      UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  -- engineer invitations: the inviting clinic. clinic invitations: the
  -- clinic the invited account set up, once it has.
  organization_id UUID REFERENCES fixmymedtech.organizations(id) ON DELETE SET NULL,
  engineer_kind   TEXT,
  status          TEXT NOT NULL DEFAULT 'sent',
  accepted_by     UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  accepted_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT onboarding_invitations_kind_check   CHECK (kind IN ('clinic', 'engineer')),
  CONSTRAINT onboarding_invitations_status_check CHECK (status IN ('sent', 'accepted', 'cancelled')),
  CONSTRAINT onboarding_invitations_engineer_kind_check
    CHECK (engineer_kind IS NULL OR engineer_kind IN ('internal', 'external')),
  CONSTRAINT onboarding_invitations_message_length CHECK (message IS NULL OR length(message) <= 1000)
);
CREATE INDEX IF NOT EXISTS ix_onboarding_invitations_invited_by
  ON fixmymedtech.onboarding_invitations (invited_by);
CREATE INDEX IF NOT EXISTS ix_onboarding_invitations_accepted_by
  ON fixmymedtech.onboarding_invitations (accepted_by);
CREATE INDEX IF NOT EXISTS ix_onboarding_invitations_org
  ON fixmymedtech.onboarding_invitations (organization_id);
