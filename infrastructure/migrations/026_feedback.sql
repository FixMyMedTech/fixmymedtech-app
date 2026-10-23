-- 026_feedback.sql
-- Feedback and issue reports sent from the floating "?" button on every page.
--
-- Each row is stored first and then posted to a Discord forum channel as its
-- own thread (one thread per report). discord_status tracks that second step,
-- so nothing is lost when Discord is down or the webhook is not configured:
--   pending  → saved, Discord post not attempted yet
--   sent     → thread created (discord_thread_id holds its id)
--   failed   → the webhook call failed; see the backend log
--   disabled → no DISCORD_FEEDBACK_WEBHOOK_URL configured
--
-- profile_id is set when the sender was logged in. contact_email is only
-- filled by anonymous senders who want a reply, and is never posted to Discord.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS fixmymedtech.feedback (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type              TEXT NOT NULL,
  summary           TEXT NOT NULL,
  description       TEXT NOT NULL,
  page              TEXT,
  lang              TEXT,
  profile_id        UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  contact_email     TEXT,
  screenshot_key    TEXT,
  discord_status    TEXT NOT NULL DEFAULT 'pending',
  discord_thread_id TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT feedback_type_check
    CHECK (type IN ('feedback', 'issue')),
  CONSTRAINT feedback_discord_status_check
    CHECK (discord_status IN ('pending', 'sent', 'failed', 'disabled'))
);

CREATE INDEX IF NOT EXISTS ix_feedback_created_at
  ON fixmymedtech.feedback (created_at DESC);
