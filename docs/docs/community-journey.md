# Community journey and skill tree: technical plan

Status: proposal, not built yet. Date: 2026-10-30.

This plan says how to build the community journey in this codebase. The product rules (which roles exist, how they unlock, what they unlock) are in the product proposal, which will move to the docs vault as feature notes. This page covers the data, the code and the build order.

## In one paragraph

Every member starts as **Ambassador**. Doing tasks unlocks **community roles** (Mapper, Verifier, Repairer, City lead…). A role brings **permissions** (approve a clinic) and **app features** (order spare parts). Points, earned on the community task board, unlock extra achievements and benefits but never roles. Roles pause after 6 months without activity. Lead roles are assigned by a community team admin. The whole tree is public.

## What already exists and is reused

| Piece | Where | Reused for |
| --- | --- | --- |
| Four activity counts per member (devices registered, faults resolved, maintenance closed, people invited), in SQL | `routers/profile.py` `_metric_subqueries`, `_counts_for` | Unlock conditions (e.g. "5 faults resolved" for Repairer) |
| Who invited whom | `users.invited_by` (migration 025) | "Invite one colleague" quest |
| Linked Discord account | `users.discord_user_id` (migration 027), `routers/discord_link.py` | "Join the Discord" quest; @mentions in unlock posts |
| Discord welcome webhook, `announce_new_device` | `config/discord.py`, `routers/discord_link.py` | "New role unlocked" posts |
| Profile country | `profiles.country` | Local roles and team ("Mapper, Ghana") |
| Superusers | `users.is_superuser`, SQLAdmin | Community team admins, for now |
| Background tasks | `utils/background.py` `spawn` | Re-checking unlocks after an action without slowing the request |
| Migration runner | `backend/migrations.py` | New tables, next number 028 |

Gaps: there is no "approved member" state today (any verified account can use the app), no city on profiles, no consent flags, no last-activity time.

## Naming: community roles, not roles

The app already has **org roles** on `org_users.role` (admin, technician, clinical_staff, engineering_staff), which decide what someone can do inside one organization. Community roles are a separate thing and must never be mixed with them. In code, tables and API they are always `community_role`, `member_role`, `/api/community/...`. The existing `/tasks` page (fault and maintenance assignments) also stays as is; the new board is "community tasks".

## Data model

One new migration, `infrastructure/migrations/028_community_roles.sql`, plus matching classes in `models/models.py`. All tables in schema `fixmymedtech`.

### The catalogue: `community_roles`

The tree is data, so the community team can grow it without a release.

| Column | Type | Notes |
| --- | --- | --- |
| `key` | text, primary key | `ambassador`, `mapper`, `repairer`, `city_lead`… |
| `path` | text | `start`, `devices`, `people`, `trust`, `knowledge`, `teams`, `parts`, `leads` |
| `tier` | int | 0 to 3 |
| `scope` | text | `local` (held for a country, later a city) or `global` (held for a team) or `none` |
| `unlock` | text | `auto` (the app checks), `claim` (open, the member picks it), `confirmed` (needs a person to confirm one step), `assigned` (admins only: leads) |
| `names` | jsonb | `{"en": "Repairer", "fr": "Réparateur", "es": "Reparador"}` |
| `descriptions` | jsonb | Same shape |
| `linkedin_titles` | jsonb | Same shape, for the share kit |
| `sort` | int | Order inside its path |
| `active` | bool | Hide a role without deleting history |

Names live in the table, not in `i18n.py`, because the catalogue is edited by the community team. Everything else on the pages (buttons, headings) follows the usual `i18n.py` rule in en/es/fr.

### `community_role_requirements`

One row per condition. All rows of a role must be met.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `role_key` | text → community_roles | |
| `kind` | text | `role` (hold another role), `metric` (a count reaches a threshold), `quest` (a one-off step), `confirmation` (a person confirms) |
| `ref` | text | Role key, metric key (`devices_registered`, `faults_resolved`, `maintenance_performed`, `invites`, later `verifications`, `manuals_added`…) or quest key |
| `threshold` | int, null | For metrics |

### `community_role_permissions`

| Column | Type | Notes |
| --- | --- | --- |
| `role_key` | text → community_roles | |
| `permission` | text | A key from the list in code (below) |

The list of permission keys lives in code (`backend/utils/community.py`, `PERMISSIONS`), because each key is checked by a router. The table only says which role grants which key. Unknown keys are refused when saved.

### `member_roles`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `profile_id` | uuid → profiles | |
| `role_key` | text → community_roles | |
| `country`, `city` | text, null | For local roles |
| `team` | text, null | For global roles: software, data, hardware, manufacturing, partnerships, communications |
| `status` | text | `active`, `removed` (paused is computed, see Pausing) |
| `source` | text | `auto`, `claim`, `confirmed`, `assigned` |
| `granted_by` | uuid → profiles, null | For confirmed and assigned roles |
| `granted_at` | timestamptz | |
| `removed_at`, `removed_reason` | | The member sees the reason |

Unique on `(profile_id, role_key, coalesce(country,''), coalesce(team,''))`, so granting twice does nothing.

### `member_quests`

For the steps the app can't count from existing tables (watched an approval meeting, introduced yourself on Discord).

| Column | Type | Notes |
| --- | --- | --- |
| `profile_id` | uuid → profiles | |
| `quest_key` | text | `profile_complete`, `discord_joined`, `consent_answered`, `colleague_invited`, `first_contribution`, `watched_approval_meeting`… |
| `count` | int | For quests done several times (watched 2 meetings) |
| `confirmed_by` | uuid → profiles, null | |
| `updated_at` | timestamptz | |

Quests that can be read from existing data (`discord_joined` = `users.discord_user_id is not null`, `colleague_invited` = someone has `invited_by` = me) are computed, not stored.

### New columns on `profiles`

| Column | Type | Why |
| --- | --- | --- |
| `city` | text | Local roles, members page |
| `country_trained` | text | Member story ("I was trained in…") |
| `why_bme` | text, ≤ 500 | Member story ("I chose biomedical engineering because…") |
| `member_status` | text default `pending` | `pending` until the approval meeting, then `member` |
| `member_since` | timestamptz | |
| `social_consent` | bool, null | Null = not answered yet. Asked on its own page |
| `social_consent_at` | timestamptz | |
| `members_page_hidden` | bool default false | The member hid their card |
| `last_active_at` | timestamptz | For pausing |

Backfill in the same migration: every existing profile becomes `member_status = 'member'` and gets the Ambassador role, so nobody already on the platform loses access.

## Unlock engine: `backend/utils/community.py`

One module, no framework.

- `progress(db, profile_id) -> dict`: for every role, which requirements are met and how far (`3 of 5`). Reuses `_counts_for` from `routers/profile.py`, moved into this module or imported, so the journey page, the Network directory and the unlock rules always count the same way.
- `check_unlocks(db, profile_id) -> list[str]`: grants every `auto` role whose requirements are all met and returns the new keys. Idempotent thanks to the unique constraint.
- `has_permission(db, profile, permission, country=None) -> bool`: true if the member holds an active, not paused role that grants it (in that country, for local roles). Superusers always pass.
- `require_permission(permission)`: a FastAPI dependency for routers.

When it runs: after the actions that can change progress, through `spawn(...)` so the request is not slowed. That is device created (`routers/devices.py`), fault resolved and maintenance closed, invite accepted, Discord linked, profile saved. Also on every visit to the journey page, as a safety net.

On a new unlock: post to Discord with the existing welcome webhook (one line, same style as `announce_new_device`), and store the role key so the next page view shows the unlock screen once.

## Pausing after 6 months

No scheduler is needed. `last_active_at` is updated (at most once a day) by `get_current_profile` in `utils/profile.py`. A role counts as paused when `last_active_at` is more than 6 months ago, computed when it is read, so the first action back un-pauses everything at once. The 5-month reminder email needs a daily job; it waits for phase 4.

## Approval and the Ambassador role

- Sign-up creates a profile with `member_status = 'pending'`. Nothing in the app changes for them yet, apart from a "Book your welcome meeting" card on the home page and the journey page.
- A community team admin approves the member after the meeting: `member_status = 'member'`, `member_since = now()`, Ambassador granted.
- Accounts created through an engineer's invitation are approved at once (decision #15 in the vault).

## Permissions and features

Phase 1 gates nothing that exists today. Later phases add checks with `require_permission(...)`:

| Permission | Granted by | Checked in |
| --- | --- | --- |
| `claim_verification_tasks` | Verifier | Community task board (not built yet) |
| `approve_members`, `approve_clinics` | Approval host, community team | Community admin pages, clinic approval |
| `receive_area_repair_requests` | Repairer | Public "request maintenance" flow |
| `diagnose_outside_my_orgs` | Repairer | `routers/fault_reports.py` steps 3 and 5, today limited to the assignee |
| `order_spare_parts` | Repairer only | Spare parts catalogue (not built yet) |
| `publish_part_designs` | Part designer | Parts library (not built yet) |
| `approve_part_designs` | Design reviewer | Parts library |
| `supply_restricted_parts` | Certified maker (with a valid quality certificate) | Spare parts catalogue |
| `assign_roles` | Community team | Community admin pages |

The fault workflow keeps its own org-based rules. A community permission can only add a way in, never remove one an org role already gives.

## API: `backend/routers/community.py`, mounted at `/api/community`

| Method and path | Who | Returns |
| --- | --- | --- |
| `GET /tree` | Public | The catalogue: roles, paths, requirements, in the asked language |
| `GET /me` | Member | My roles (with paused flag), progress per role, welcome quests, next tasks |
| `POST /me/claim/{role_key}` | Member | Takes a `claim` role whose requirements are met |
| `POST /me/consent` | Member | `{social: true/false}` |
| `PATCH /me/story` | Member | city, country_trained, why_bme |
| `GET /public/members` | Public | Listed members only: name, photo key, country, city, roles. No email, no ids beyond the profile id |
| `GET /public/stats` | Public | Engineers, countries, members per country (for the "I joined" post and fixmymedtech.org) |
| `GET /admin/pending` | `approve_members` | Profiles waiting for approval |
| `POST /admin/members/{id}/approve` | `approve_members` | Approves, grants Ambassador |
| `POST /admin/members/{id}/roles` | `assign_roles` | Assigns a role (leads, confirmations) |
| `DELETE /admin/member-roles/{id}` | `assign_roles` | Removes a role, with a reason |

Responses are built by hand from columns, never by returning ORM rows (the `Profile.user` / `hashed_password` pitfall in `routers/fault_reports.py`). The two `/public/...` endpoints need CORS for fixmymedtech.org once the static site reads them; add the origin to the backend's CORS settings then.

## Frontend: `frontend/features/community/`

Same pattern as the other features.

| File | Path | Content |
| --- | --- | --- |
| `api.py` | | Wrappers with `_get/_post/_patch` from `config/api.py` |
| `pages/journey.py` | `/community` | My journey: current roles, next unlock with progress, next tasks, welcome quests |
| `pages/tree.py` | `/community/tree` | The skill tree, public (`pub_shell`) or personal (`page_shell`) |
| `pages/role.py` | `/community/roles/{key}` | Role page: what it does, how to unlock, what it unlocks, LinkedIn title, Claim button |
| `pages/welcome.py` | `/community/welcome` | Shown once after approval: welcome and social media consent |
| `pages/admin.py` | `/community/admin` | Pending members, assign or remove roles |

- Register every router in `frontend/main.py` with `xxx.rt.to_app(app)`.
- Add `("/community", "community", _("nav.community"))` to `sidebar()` in `components.py`, with a Lucide icon.
- New strings in `i18n.py` for en, es and fr.
- Add the member's role keys and `member_status` to what `UserContextMiddleware` caches from `/api/auth/me`, and refresh them after an unlock or an approval.
- The tree is server-rendered HTML and CSS (a grid of cards, like the design canvas), no JS library. The screens to follow are in the "Community journey screens" design canvas.

## Build order

Each phase is one pull request against `dev`.

**Phase 1: Ambassador and the journey page.** Migration 028 with the catalogue seeded from the proposal, approval state and backfill, `utils/community.py` (`progress`, Ambassador grant), `GET /tree`, `GET /me`, consent and story endpoints, admin approve and assign, pages journey, tree, role (read only), welcome, admin. Nothing in the existing app is gated.

**Phase 2: unlocking.** `check_unlocks` wired into the actions above, claiming tier 1 roles, tier 2 automatic unlocks, the unlock screen, Discord posts, share kit link.

**Phase 3: roles that do something.** Confirmations (watched meetings), first permission checks (approvals, fault steps outside my orgs, area repair requests), link to the community task board when it exists.

**Phase 4: leads and upkeep.** City and country dashboards, pause reminders (daily job), tree editor for admins (SQLAdmin views of the three catalogue tables are a cheap first version), public members page and stats for fixmymedtech.org.

Spare parts permissions wait for the parts library and catalogue features themselves.

## Testing

The repo has no test suite. Phase 1 adds `backend/tests/test_community.py` with pytest for the unlock engine (requirements met or not, idempotent grant, paused computation), since that logic decides who can do what. Pages are checked by hand on the local stack (`docker compose -f docker-compose.local.yml up --build`) with the seeded test users from `scripts/seed_test_data.py`.

## Open technical questions

- Community team admins are superusers for now. When the community team grows, should it become its own community role with `assign_roles` (already in the catalogue) instead of superuser access?
- Local roles are held per country first. Are cities needed from phase 1, or can they wait until there are City leads?
