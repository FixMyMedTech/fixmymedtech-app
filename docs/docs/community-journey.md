# Community journey and skill tree: technical plan

Status: phase 1 built (migration 029), see the [how-to guide](community-guide.md). Date: 2026-10-30. Screens: the "Community journey screens" design canvas.

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
| Migration runner | `backend/migrations.py` | New tables, migration 029 (028 was taken) |

Gaps: there is no applicant or member state today (any verified account can use the whole app), no city on profiles, no consent flags, no last-activity time.

## Naming: community roles, not roles

The app already has **org roles** on `org_users.role` (admin, technician, clinical_staff, engineering_staff), which decide what someone can do inside one organization. Community roles are a separate thing and must never be mixed with them. In code, tables and API they are always `community_role`, `member_role`, `/api/community/...`. The existing `/tasks` page (fault and maintenance assignments) also stays as is; the new board is "community tasks".

## Data model

One new migration, `infrastructure/migrations/029_community_roles.sql`, plus matching classes in `models/models.py`. All tables in schema `fixmymedtech`.

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
| `quest_key` | text | `intro_video`, `meeting_held`, `watched_approval_meeting`… |
| `count` | int | For quests done several times (watched 2 meetings) |
| `confirmed_by` | uuid → profiles, null | |
| `updated_at` | timestamptz | |

Quests that can be read from existing data (`profile_complete`, `discord_joined` = `users.discord_user_id is not null`, `consent_answered` = `profiles.social_consent is not null`) are computed, not stored.

### `community_role_changes`

An append-only log: `id`, `actor_id`, `action` (`role_created`, `role_edited`, `role_assigned`, `role_removed`, `applicant_decided`…), `target` (role key, member or applicant id), `before` and `after` (jsonb), `reason`, `created_at`.

### New columns on `profiles`

| Column | Type | Why |
| --- | --- | --- |
| `city` | text | Local roles, members page |
| `country_trained` | text | Member story ("I was trained in…") |
| `why_bme` | text, ≤ 500 | Member story ("I chose biomedical engineering because…") |
| `member_status` | text default `applicant` | `applicant` until the Ambassador quests are done, then `member`; `staff` for invited clinic staff who watched the video; `refused` if the meeting ends in a refusal |
| `member_since` | timestamptz | When the quests were completed (or the migration date for existing accounts) |
| `social_consent` | bool, null | Null = not answered yet. Asked on its own page |
| `social_consent_at` | timestamptz | |
| `members_page_hidden` | bool default false | The member hid their card |
| `last_active_at` | timestamptz | For pausing |

Backfill in the same migration: every existing profile gets `member_status = 'member'`, `member_since` and the Ambassador role, so nobody already on the platform loses access.

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

## Joining: `/join` creates the account

`/join` is the one way into the community. It creates an account straight away, but the account is a **community applicant**: it can only use the journey pages until the Ambassador quests are done. Then platform access opens.

### The form: `/join` (public, replaces `/signup`)

Name, email, password, country, city, "I am a…" (biomedical engineer, student, clinician, other), organisation or school, country trained in, why you want to join, how you heard of us. A referral code in the link (`/join?ref=CODE`) sets `invited_by`, so the member who shared gets the credit. The existing email verification still applies. `/signup` redirects to `/join`.

### What the applicant sees: `/community/start`

Every page of the platform redirects an applicant here. It shows:

1. the **intro video** (embedded; the quest is done when the video ends, or with an "I've watched it" button as a fallback),
2. **book a welcome meeting** with a member of the community (a booking link, see below),
3. the Ambassador quests as a checklist with progress,
4. the Discord invite and a preview of the skill tree.

### The Ambassador quests

| Quest | Done when | Checked |
| --- | --- | --- |
| Complete your profile | Photo, country, city, country trained in, why you joined | Automatic |
| Watch the intro video | The video reached its end | Automatic |
| Meet a member of the community | The host marks the meeting as held | Confirmed by an Approval host or the community team |
| Join the Discord | `users.discord_user_id` is set | Automatic |
| Answer the social media consent | `profiles.social_consent` is not null (yes or no) | Automatic |

When the last one is done, the member gets **Ambassador**, `member_status` becomes `member`, and the platform opens with a welcome screen. "Invite a colleague" and "first device or first community task" move to the tier 1 roles, since they need the platform.

### Booking the meeting

Phase 1 keeps it simple: one booking link (for example a shared Cal.com or Calendly page of the Approval hosts, set in `COMMUNITY_BOOKING_URL`), and the host records the meeting in the dashboard. A built-in calendar can come later.

### Table: `community_applications`

The join form answers and the meeting, one row per applicant, linked to their profile.

| Column | Type | Notes |
| --- | --- | --- |
| `profile_id` | uuid → profiles, primary key | |
| `kind` | text | `engineer`, `student`, `clinician`, `other` |
| `organisation`, `motivation`, `heard_from` | text | |
| `host_id` | uuid → profiles, null | The member who meets them |
| `meeting_at` | timestamptz, null | |
| `meeting_held_at`, `meeting_confirmed_by` | | Completes the meeting quest |
| `notes` | text | Internal, never shown to the applicant |
| `status` | text | `open`, `meeting_booked`, `met`, `refused`, `withdrawn` |
| `decision_reason` | text | When refused |
| `created_at`, `updated_at` | timestamptz | |

A refused applicant keeps an account that can only see a message with the reason. Refused and withdrawn applications are deleted after 12 months.

### Gating the platform

- **Backend:** a new dependency `get_member_profile` in `utils/profile.py`: the same as `get_current_profile`, plus a `403 {"detail": "community_access_pending"}` when `member_status` is not `member` or `staff`. Staff pass it, but hold no community role, so every community permission check still refuses them. Every platform router switches to it (devices, faults, maintenance, organizations, dashboard, tasks…). The profile, Discord, community and auth routes keep `get_current_profile`, so applicants can do their quests. Public `/public/...` routes don't change. *As built:* the check is one dependency, `require_platform_access`, attached to those routers in `main.py` rather than a change in every route.
- **Frontend:** `require_auth` in `features/auth/helper.py` reads `member_status` from the session (cached by `UserContextMiddleware` from `/api/auth/me`) and redirects applicants to `/community/start`. When the API answers `community_access_pending`, the session is refreshed and the same redirect happens.

### Existing and invited accounts

- Every existing account is backfilled as a member with Ambassador, so nobody loses access.
- **Clinic staff invited by a clinic** (organisation invitation, `routers/organizations.py`) only have to **watch the video** before they get in (Jason, 2026-10-30). Their status becomes `staff`: they use the app inside their clinic with their org role (report faults, see devices, log maintenance), but hold no community role.
- If they want more (community tasks, roles, the features roles unlock), they do the remaining Ambassador quests from the same start page: profile, meeting, Discord, consent. Then they become Ambassador and `member`, like everyone else.
- The video quest is the same `intro_video` quest. The main video URL is `COMMUNITY_INTRO_VIDEO_URL`; a shorter clinic-staff video can be set separately (`STAFF_INTRO_VIDEO_URL`, falling back to the main one).

## Permissions and features

Phase 1 only adds the applicant gate above. Role permissions start in later phases, with `require_permission(...)`:

| Permission | Granted by | Checked in |
| --- | --- | --- |
| `claim_verification_tasks` | Verifier | Community task board (not built yet) |
| `decide_applicants`, `approve_clinics` | Approval host, community team | Applicants tab, clinic approval |
| `receive_area_repair_requests` | Repairer | Public "request maintenance" flow |
| `diagnose_outside_my_orgs` | Repairer | `routers/fault_reports.py` steps 3 and 5, today limited to the assignee |
| `order_spare_parts` | Repairer only | Spare parts catalogue (not built yet) |
| `publish_part_designs` | Part designer | Parts library (not built yet) |
| `approve_part_designs` | Design reviewer | Parts library |
| `supply_restricted_parts` | Certified maker (with a valid quality certificate) | Spare parts catalogue |
| `manage_roles`, `assign_roles`, `view_members`, `view_applicants`, `view_role_history` | See the dashboard section | Community admin dashboard |

The fault workflow keeps its own org-based rules. A community permission can only add a way in, never remove one an org role already gives.

## The community admin dashboard: `/community/admin`

One dashboard with four tabs. What each person sees depends on their permissions, so the same pages serve the community team and the leads.

| Tab | What it does | Permission |
| --- | --- | --- |
| **Applicants** | New accounts still doing their quests: quest progress, filter by status and country, assign a host, record the meeting (which completes that quest), or refuse with a reason | `view_applicants`, `decide_applicants` |
| **Members** | Every member with their roles, country, city, last activity and activity counts. Open a member: their roles and history, add or remove a role | `view_members`, `assign_roles` |
| **Roles** | The tree as a list. Create a role, edit its names, path, tier, unlock type, requirements and permissions, or retire it | `manage_roles` |
| **History** | Every change to roles, permissions and applications: who, what, when | `view_role_history` |

### Creating a role

**Roles › New role** opens one form:

- names, description and LinkedIn title in English, French and Spanish,
- path, tier, scope (local, global team, none),
- how it unlocks: automatic, claimed by the member, confirmed by a person, or assigned by an admin,
- requirements: rows of "hold role X", "count Y reaches N", "quest Z done", "confirmed by a holder of role W",
- permissions: every key from `PERMISSIONS` as a checkbox with its plain description, grouped (community, devices and repairs, spare parts, admin).

Saving checks that every requirement points to a real role, metric or quest and that the tree has no loops. A new role starts as a draft, visible only in the dashboard, until an admin publishes it to the tree.

### Assigning a role

From **Members**, open a member and click **Add role**: pick the role, the country or team it applies to, and a reason. The member gets a notification and the unlock screen on their next visit, and the change goes in History. Removing works the same way, and the reason is shown to the member.

### Permissions for the dashboard itself

| Permission | Given to |
| --- | --- |
| `manage_roles` (edit the tree and its permissions) | Community team admins only |
| `assign_roles` (give or remove any role) | Community team admins only |
| `view_applicants`, `decide_applicants` | Community team, Approval hosts (in their country) |
| `view_members` | Community team (everyone), City and Country leads (their country), Team leads (their team) |
| `view_role_history` | Community team |

Superusers have every permission, so the first admins need nothing set up.

## Members list for leads

Leads open **Members** in the same dashboard, limited to their scope: a Country lead sees the members of their country, a Team lead the members of their team, the community team everyone.

For each member: name, photo, city, roles (with paused ones marked), member since, last active, and their actions: devices registered, faults resolved, maintenance done, people invited, community tasks done, and the date of their last action. A member's page shows the timeline of their roles and contributions.

Leads can see but not change roles. They can flag a member to the community team ("ready for Repairer", "inactive, contact them"). Email and phone are shown to leads only for members in their scope.

## Adding new roles later

Two cases, depending on whether the new role needs a new kind of access.

1. **A new role made of existing permissions** (for example a "Trainer" who can confirm quests and create local tasks): no code, no release. A community team admin adds the role, its requirements and its permissions in the admin. It appears in the tree at once.
2. **A role that needs a new kind of access** (for example "can publish training videos"): a small code change. A developer adds the permission key to `PERMISSIONS` in `utils/community.py` and one `require_permission("publish_training")` line on the router that does the action, in one pull request. Once it is deployed, admins attach the key to any role in the admin, as in case 1.

So the code only ever answers "what can be done", and the admin decides "who can do it". Every key has a short description in `PERMISSIONS`, which the admin shows next to the checkbox, so admins see what they are granting. Every change to roles and their permissions is logged (who, when, what) in a `community_role_changes` table, shown in the dashboard's History tab, and recorded in the decisions log.

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
| `GET /admin/applicants` | `view_applicants` | Applicants with quest progress, in the caller's scope |
| `PATCH /admin/applicants/{id}` | `decide_applicants` | Status, assignee, meeting, notes |
| `POST /admin/applicants/{id}/meeting-held` | `decide_applicants` | Completes the meeting quest; grants Ambassador if it was the last one |
| `POST /admin/applicants/{id}/refuse` | `decide_applicants` | With a reason |
| `POST /me/quests/intro_video` | Applicant | Marks the intro video as watched |
| `GET /admin/members` | `view_members` | Members with roles and activity, in the caller's scope |
| `GET /admin/members/{id}` | `view_members` | One member's roles and timeline |
| `GET /admin/roles`, `POST /admin/roles`, `PATCH /admin/roles/{key}` | `manage_roles` | The catalogue with requirements and permissions |
| `GET /admin/permissions` | `manage_roles` | The keys from `PERMISSIONS` with descriptions |
| `GET /admin/history` | `view_role_history` | The change log |
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
| `pages/join.py` | `/join` | The public join form; creates the account |
| `pages/start.py` | `/community/start` | Applicant home: intro video, book a meeting, quests |
| `pages/admin_applicants.py` | `/community/admin/applicants` | Applicants, their quests and meetings |
| `pages/admin_members.py` | `/community/admin/members` | Members list and member page, add or remove roles |
| `pages/admin_roles.py` | `/community/admin/roles` | Role list and role editor |
| `pages/admin_history.py` | `/community/admin/history` | Change log |

- Register every router in `frontend/main.py` with `xxx.rt.to_app(app)`.
- Add `("/community", "community", _("nav.community"))` to `sidebar()` in `components.py`, with a Lucide icon.
- New strings in `i18n.py` for en, es and fr.
- Add the member's role keys and permissions to what `UserContextMiddleware` caches from `/api/auth/me`, and refresh them after an unlock or an approval.
- The tree is server-rendered HTML and CSS (a grid of cards, like the design canvas), no JS library. The screens to follow are in the "Community journey screens" design canvas.

## One app: joining the platform and the community

The community is not a second app. It is a second half of the same app: one login, one sidebar, one profile, one task list. The screens are in the "One app: work and community together" row of the design canvas.

### Navigation

`sidebar()` in `components.py` becomes grouped:

| Group | Links | Notes |
| --- | --- | --- |
| (top) | Home | |
| Work | Devices, Faults, Tasks, Clinics | Clinics is today's Groups page (`/groups`), renamed in the UI only; URLs stay |
| Community | My journey, Skill tree, Members | Members replaces Network (`/network` redirects to `/community/members`) |
| Admin | Community admin | Only when the member has a dashboard permission |
| (bottom) | Profile, language, theme | |

- Links are data: each entry may carry a required permission, and `sidebar()` skips the ones the member lacks. Applicants see only "Start" and Profile.
- On phones, a bottom bar with Devices, Faults, Community and Profile (Community opens My journey; the rest of the sidebar stays in the menu). It is new CSS in `components.py`, shown under 760 px.
- The member's roles and permissions are cached in the session by `UserContextMiddleware` (as the avatar data is today), so building the sidebar costs no API call.

### Home: the bridge

`/home` (today a landing card) becomes the member's home:

1. **Next unlock** card: the closest role and its progress, with what it unlocks. From `GET /api/community/me`.
2. **Open faults** and **Maintenance due**: from the existing `/api/dashboard/stats` and fault list, five lines each.
3. **Community tasks near you**: from the community task board when it exists; hidden until then.
4. **Near you this week**: a short line of local activity (from the activity feed plan).

The landing card stays for visitors who are not signed in.

### One profile

`/profile` and the public profile (`/profile/{id}`) show three things on one page: clinic memberships with their org roles (today's content), community roles with their country or team, and achievements and points. A line explains the difference: clinic roles are set by each clinic, community roles come from the skill tree. "Share my roles on LinkedIn" opens the share kit.

### One task inbox

`/tasks` keeps its URL and gets two tabs: **My jobs** (today's fault and maintenance assignments, unchanged) and **Community** (the community tasks the member picked up or that their roles offer). The sidebar badge counts both. The community task board itself stays at `/community/tasks`.

### Work feeds progress

After an action that counts toward a role (device registered, fault resolved, maintenance closed, colleague invited), the page shows a small banner: "Fault resolved. 4 of 5 toward Repairer", linking to My journey.

- The backend returns the progress with the action's response (`"community": {"role": "repairer", "done": 4, "needed": 5}`), computed by `utils/community.py`, so no second request is needed.
- The frontend shows it with a new `progress_toast()` component in `components.py`, after the redirect that follows the form (kept for one request in the session, like a flash message).
- If the action unlocked a role, the full unlock screen shows instead.

### Locked features stay visible

A feature that a role unlocks is shown to everyone, locked for those who don't have it: a dashed button with a padlock and "Unlock as Repairer", linking to the role page. Members meet the skill tree where they work.

- One helper, `locked_action(label, role_key, lang)` in `components.py`, used wherever a gated action would appear (order spare parts, plan maintenance for a clinic, approve a clinic…).
- The backend still refuses the action (`require_permission`); the locked button is only a signpost.
- Lead and admin screens are hidden, not shown locked: only features that are part of the skill tree show a padlock.

### Look and feel

- One design system for both halves (the FixMyMedTech design system: tokens, badges, buttons). No separate community theme.
- Community moments (unlock screen, progress banner, welcome) use `brand-deep` (#01437a) with white text, so they stand out without feeling like another product.
- The community side follows the same i18n rule (en, es, fr) and the same "hospital words" voice.

### Files touched

| File | Change |
| --- | --- |
| `frontend/components.py` | Grouped `sidebar()` with permission-aware links, phone bottom bar, `progress_toast()`, `locked_action()` |
| `frontend/main.py` | `UserContextMiddleware` caches roles, permissions and `member_status`; register community routers |
| `frontend/features/home/pages.py` | New member home |
| `frontend/features/profile/pages/my_profile.py`, `profile_detail.py` | Community roles and achievements sections |
| `frontend/features/tasks/pages.py` | Two tabs |
| `frontend/features/network/pages.py` | Redirect to `/community/members` once Members exists |
| `frontend/features/groups/...` | UI label "Clinics" (i18n strings only) |
| `backend/routers/devices.py`, `fault_reports.py`, `maintenance_logs.py`, `organizations.py` | Add the `community` progress block to the responses of counting actions |
| `frontend/i18n.py` | New strings in en, es, fr |

## Build order

Each phase is one pull request against `dev`.

**Phase 1: joining, Ambassador and the dashboard.** Migration 029 with the catalogue seeded from the proposal, `community_applications`, `community_role_changes` and the backfill; `utils/community.py` (`progress`, `has_permission`, Ambassador quests and grant); `/join` and `/community/start` with the intro video and booking link; the platform gate (`require_platform_access`, `require_auth` redirect); the dashboard tabs Applicants, Members and History, and Roles read-only with assign and remove; `GET /tree`, `GET /me`, consent and story endpoints; pages journey, tree, role (read only), welcome. Existing accounts keep full access through the backfill.

**Phase 1b: the role editor.** Create and edit roles, requirements and permissions in the dashboard (until then, the catalogue is edited through SQLAdmin).

**Phase 2: unlocking and one app.** `check_unlocks` wired into the actions above, claiming tier 1 roles, tier 2 automatic unlocks, the unlock screen, Discord posts, share kit link. The grouped sidebar and phone bottom bar, the new home, the combined profile, the two-tab task inbox, progress banners and locked actions.

**Phase 3: roles that do something.** Confirmations (watched meetings), first permission checks (approvals, fault steps outside my orgs, area repair requests), link to the community task board when it exists.

**Phase 4: leads and upkeep.** City and country dashboards with local stats, flags from leads, pause reminders (daily job), public members page and stats for fixmymedtech.org.

Spare parts permissions wait for the parts library and catalogue features themselves.

## Testing

The repo has no test suite. Phase 1 adds `backend/tests/test_community.py` with pytest for the unlock engine (requirements met or not, idempotent grant, paused computation), since that logic decides who can do what. Pages are checked by hand on the local stack (`docker compose -f docker-compose.local.yml up --build`) with the seeded test users from `scripts/seed_test_data.py`.

## Open technical questions

- Community team admins are superusers for now. When the community team grows, should it become its own community role with `manage_roles` and `assign_roles` instead of superuser access?
- Intro and staff videos are hosted on YouTube (Jason, 2026-10-30): embed with the IFrame Player API (`youtube-nocookie.com`) and mark the quest done on the `ENDED` state, keeping the "I've watched it" fallback button.
- Gating the platform touches every router's dependency. It is a mechanical change but a wide one: phase 1 should land it in its own commit, checked page by page with an applicant account and a member account.
- Local roles are held per country first. Are cities needed from phase 1, or can they wait until there are City leads?
