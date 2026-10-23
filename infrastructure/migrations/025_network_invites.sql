-- 025_network_invites.sql
-- The Network directory is ordered by how active each member is, and one of
-- those measures is how many people they have brought onto the platform.
--
-- invited_by records who created the account, so that credit is available
-- even after the inviter's own membership of an organization ends. It is
-- deliberately set only when an account is FIRST created: inviting someone
-- who already has an account must not rewrite their original attribution.
--
-- The FK is declared here in SQL only. Declaring it in the ORM as well made
-- User.profile ambiguous (two paths back to Profile), so models.py carries
-- invited_by as a plain column with no ForeignKey().
--
-- Idempotent: safe to re-run.

ALTER TABLE fixmymedtech.users
  ADD COLUMN IF NOT EXISTS invited_by UUID;

ALTER TABLE fixmymedtech.users
  DROP CONSTRAINT IF EXISTS fk_users_invited_by;

ALTER TABLE fixmymedtech.users
  ADD CONSTRAINT fk_users_invited_by
  FOREIGN KEY (invited_by) REFERENCES fixmymedtech.profiles(id)
  ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_users_invited_by
  ON fixmymedtech.users (invited_by);
