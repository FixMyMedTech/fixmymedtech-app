-- 032_call_an_engineer.sql — wave 4 ("Call an engineer", ride-style flow)
--
-- A clinic calls an engineer on a fault. Engineers are told in order
-- (fault_call_notices.tier): the clinic's own engineers first, then the
-- engineer who registered the device, then Contributors in the clinic's
-- city once the call widens. Each engineer may send one visit offer
-- (visit fee + arrival time); the clinic may counter it once; accepting an
-- offer assigns the fault (today's "assign" step). After the repair the
-- clinic signs off and rates it (fault_ratings).
--
-- Payment stays outside the app: fees are recorded, nothing is charged.
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.fault_reports
  ADD COLUMN IF NOT EXISTS call_status     TEXT,
  ADD COLUMN IF NOT EXISTS urgency         TEXT,
  ADD COLUMN IF NOT EXISTS call_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS call_started_by UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS call_widened_at TIMESTAMPTZ;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.fault_reports ADD CONSTRAINT fault_reports_call_status_check
    CHECK (call_status IS NULL OR call_status IN ('searching', 'agreed', 'closed'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.fault_reports ADD CONSTRAINT fault_reports_urgency_check
    CHECK (urgency IS NULL OR urgency IN ('now', 'this_week'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS fixmymedtech.fault_call_notices (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fault_id    UUID NOT NULL REFERENCES fixmymedtech.fault_reports(id) ON DELETE CASCADE,
  engineer_id UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  tier        TEXT NOT NULL,
  notified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  passed_at   TIMESTAMPTZ,
  CONSTRAINT fault_call_notices_tier_check CHECK (tier IN ('responsible', 'registrant', 'city')),
  CONSTRAINT fault_call_notices_once UNIQUE (fault_id, engineer_id)
);

CREATE TABLE IF NOT EXISTS fixmymedtech.fault_offers (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fault_id     UUID NOT NULL REFERENCES fixmymedtech.fault_reports(id) ON DELETE CASCADE,
  engineer_id  UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  visit_fee    NUMERIC(12, 2) NOT NULL,
  currency     TEXT NOT NULL DEFAULT 'XAF',
  arrival_at   TIMESTAMPTZ NOT NULL,
  note         TEXT,
  -- pending → accepted | countered → accepted | declined; withdrawn; lapsed
  status       TEXT NOT NULL DEFAULT 'pending',
  counter_fee  NUMERIC(12, 2),
  counter_note TEXT,
  countered_by UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  countered_at TIMESTAMPTZ,
  agreed_fee   NUMERIC(12, 2),
  decided_by   UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  decided_at   TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fault_offers_status_check
    CHECK (status IN ('pending', 'countered', 'accepted', 'declined', 'withdrawn', 'lapsed')),
  CONSTRAINT fault_offers_fee_check CHECK (visit_fee >= 0 AND (counter_fee IS NULL OR counter_fee >= 0)),
  CONSTRAINT fault_offers_one_per_engineer UNIQUE (fault_id, engineer_id)
);

CREATE TABLE IF NOT EXISTS fixmymedtech.fault_ratings (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fault_id   UUID NOT NULL UNIQUE REFERENCES fixmymedtech.fault_reports(id) ON DELETE CASCADE,
  engineer_id UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  rated_by   UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  rating     INTEGER NOT NULL,
  comment    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fault_ratings_rating_check CHECK (rating BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS fault_offers_engineer_idx ON fixmymedtech.fault_offers (engineer_id);
CREATE INDEX IF NOT EXISTS fault_call_notices_engineer_idx ON fixmymedtech.fault_call_notices (engineer_id);
CREATE INDEX IF NOT EXISTS fault_ratings_engineer_idx ON fixmymedtech.fault_ratings (engineer_id);
