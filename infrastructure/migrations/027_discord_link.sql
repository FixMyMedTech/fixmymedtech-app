-- 027_discord_link.sql
-- Link an app account to a Discord account.
--
-- discord_user_id is Discord's numeric user id (a snowflake, stored as text).
-- It is set from "Connect Discord" on the profile page, or when someone logs
-- in with Discord. One Discord account can be linked to one app account only.
--
-- discord_welcomed_at is set once the welcome message has been posted in the
-- Discord welcome channel. It is kept when the account is disconnected, so
-- reconnecting later does not post a second welcome.
--
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.users
  ADD COLUMN IF NOT EXISTS discord_user_id     TEXT,
  ADD COLUMN IF NOT EXISTS discord_username    TEXT,
  ADD COLUMN IF NOT EXISTS discord_linked_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS discord_welcomed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_discord_user_id
  ON fixmymedtech.users (discord_user_id)
  WHERE discord_user_id IS NOT NULL;
