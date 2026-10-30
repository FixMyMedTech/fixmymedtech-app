# Brief for Claude Code: community journey

This folder is the handoff for building the community journey in `fixmymedtech-app`. Read it before writing code. It points to the plan, lists which features from the docs vault (`fixmymedtech-docs`) are in scope, and sets the design rules.

## 1. Read first, in this order

1. `CLAUDE.md` at the repo root: stack, commands, conventions (migrations, i18n, serialization pitfall, router registration).
2. `docs/docs/community-journey.md`: the technical plan. Data model, unlock engine, `/join`, gating, permissions, admin dashboard, API, frontend files, "One app" integration, build order. **It is the source of truth for what to build.**
3. `docs/design-system/README.md` and `docs/design-system/tokens.json`: the FixMyMedTech design system. Every new or touched screen uses it (section 4).
4. `docs/implementation/community-journey/screens/*.dc.html`: static mockups of every screen (section 5). Open them in a browser or read the markup for layout, copy and states. Ignore the missing `support.js` and the `<x-dc>` wrapper; they come from the design tool.

The live design canvas is https://claude.ai/artifact/UEep9YybtPm2NmQBCa8ZC6 and the design system artifact is https://claude.ai/artifact/ThYn6W5ipV8TiHeZMxSKp7. The copies in this repo were taken on 2026-10-30; if Jason says the canvas changed, ask him for a fresh export.

## 2. Features from the docs vault to implement

The vault lives in `github.com/FixMyMedTech/fixmymedtech-docs` (`04-roadmap/features/*.en.md`). Feature notes there describe *what*; the plan in this repo describes *how*. Where they disagree, the newer decision wins (section 6).

| Vault feature note | Vault release | What to build here | Phase |
| --- | --- | --- | --- |
| `sign-up-and-invitations` | 1 | `/join` replaces `/signup` and creates the account. Keep invite links: `invited_by` is stored and shown ("Invited by …"). Clinic invites to clinic staff keep working, with the staff video gate. | 1 |
| `clinic-approval` | 1 | The welcome meeting reuses the same booking link and the same "community team runs meetings" rule. Applicants are listed in `/community/admin` › Applicants. Organisation approval itself is unchanged in this work; only people join through the quests. | 1 |
| *new:* community journey and skill tree | — | Catalogue tables, `member_roles`, `member_quests`, unlock engine, Ambassador quests, `/community/start`, journey, tree and role pages. | 1, 2 |
| *new:* community admin dashboard | — | `/community/admin` with Applicants, Members, Roles, History; assign and remove roles; role editor in 1b. | 1, 1b |
| *new:* roles and permissions for community roles | — | `community_role_permissions`, `has_permission`, `require_permission`, permission keys in `utils/community.py`. Does **not** replace org roles on `org_users.role`. | 1, 3 |
| `member-share-kit` (draft, member-sharing) | — | Consent quest and `social_consent`; "Share my roles on LinkedIn" link on the profile and the unlock screen. The LinkedIn post queue itself is not in the app. | 1 (consent), 2 (share link) |
| `role-paths` (draft, member-sharing) | — | Role pages and the tree show path, tier, requirements and what each role unlocks. LinkedIn title per role (`linkedin_title`). | 1, 2 |
| `activity-feed-and-achievements` (draft) | — | Achievements on the profile and "Near you this week" on home. Points give levels and achievements, never app features. Discord posts on unlock use the existing `config/discord.py`. | 2 |
| `member-stories` (draft) | — | "Why biomedical engineering" (`why_bme`) and story fields captured at `/join` and the profile; the story endpoint. Posting stories is outside the app. | 1 |
| `community-task-board` | 2 | The Community tab of `/tasks` and the "Community tasks near you" card. Phase 2 shows quests and confirmations only; full task board (auto-created tasks, points per task) is linked in phase 3 when the board exists. | 2, 3 |
| `scan-and-fault-reporting` | 2 | No change to the flow. Resolving a fault feeds `check_unlocks` (Repairer progress) and shows the progress toast. | 2 |
| `device-registration` | 2 | No change to the flow. Registering devices feeds `check_unlocks` (Mapper progress). | 2 |
| `responsibility-and-routing` | 3 | Area repair requests become a Repairer permission (`receive_area_repair_requests`). | 3 |
| `ordering-and-requests` | 6 | Only the locked "Order spare parts · Unlock as Repairer" action. No ordering. | 2 (locked action only) |

**Out of scope for this work:** `manuals-on-device-page`, `quotes-invoices-payment-record`, `aggregated-data-for-distributors`, the spare parts catalogue and parts library (the Part designer, Maker, Design reviewer, Certified maker and Manufacturing hub lead roles exist in the catalogue but grant nothing yet), the public members page on fixmymedtech.org (phase 4), and moving money.

## 3. Phases, each one PR against `dev`

Follow "Build order" in `docs/docs/community-journey.md`. Short version:

- **Phase 1: joining, Ambassador, dashboard.** Migration `028_community_roles.sql` (next free number; check `infrastructure/migrations/` first) with seeds and backfill; `utils/community.py`; `/join`, `/community/start`; the gate; dashboard Applicants, Members, History, Roles read-only with assign and remove; journey, tree, role (read only), welcome pages; pytest for the engine.
- **Phase 1b: role editor** in the dashboard.
- **Phase 2: unlocking and one app.** `check_unlocks` wired into actions; claiming and auto-unlocking roles; unlock screen; Discord posts; grouped sidebar and phone bottom bar; new home; combined profile; two-tab `/tasks`; progress toast; locked actions; design system tokens.
- **Phase 3: roles that do something.** Confirmations, first `require_permission` checks, task board link.
- **Phase 4: leads and upkeep.** Lead dashboards, flags, pause reminders, public members export.

Phase 1 acceptance checks:

- A new person at `/join` gets an account and lands on `/community/start`; every other page redirects there until the five quests are done.
- When the host marks the meeting as held and the other quests are done, the person becomes an Ambassador (one `member_roles` row, one `community_role_changes` row) and the platform opens.
- Clinic staff invited by a clinic see only the staff video, then use their clinic; status `staff`; community pages show "do the quests to unlock more".
- Existing accounts are backfilled as `member` with Ambassador and see no change.
- A non-admin gets 403 on every `/api/community/admin/*` route.
- No response leaks `hashed_password` (build dicts by hand).
- Every new string is in `i18n.py` for `en`, `es` and `fr`.
- `pytest backend/tests/test_community.py` passes; pages checked by hand on the local stack with the seeded users.

## 4. Use the FixMyMedTech design system

Every screen built or touched in this work follows `docs/design-system/`. Do not invent colours, sizes or components.

- **Tokens:** use the 22 role-named tokens from `tokens.json` as CSS variables (`--bg`, `--surface`, `--sunken`, `--border`, `--border-strong`, `--text`, `--text-muted`, `--primary`, `--primary-hover`, `--primary-tint`, `--on-primary`, `--accent`, `--ok`, `--ok-tint`, `--warn`, `--warn-tint`, `--danger`, `--danger-tint`, `--brand-teal`, `--brand-deep`, `--brand-navy`, `--on-brand`). In phase 2, replace the `:root` block in `frontend/components.py` with these and keep the old `--c-*` names as aliases for one release (`--c-text-3: var(--text-muted)`, `--c-green: var(--ok)`, …). Phase 1 pages already use the new names; add the tokens next to the old ones if phase 2 has not landed yet.
- **Components:** take classes from `docs/design-system/components/bundle.css` and follow each component's README: Button (`btn-primary`, `btn-secondary`, `btn-danger`, `btn-sm`; merge `btn-outline` and `btn-warning` into `btn-secondary`), Badge (`badge-ok`, `badge-warn`, `badge-danger`, `badge-neutral` in `status_badge()`), Field, Card, Table, Alert, FilterPills, AppShell (sidebar and phone bottom bar), SignIn (for `/join`).
- **Status colour rule:** colour says who must act. `danger` someone must act, `warn` someone is on it, `ok` done or working, neutral not in play. Always with a word, never colour alone.
- **Type:** system fonts, 7 styles (`display` 32/700, `h1` 24/700, `h2` 20/700, `h3` 16/600, `body` 14/400 or 500, `small` 12/500, `code` 12 mono). Spacing on 4px (4, 8, 12, 16, 24, 32, 48). Radius 8 controls, 12 cards, pill for badges.
- **Brand surfaces:** the welcome headers on `/join`, `/community/start`, the welcome and unlock screens use solid `brand-deep` with an 8px `brand-teal` top border and white text. Never put text on the teal half of the gradient; never use the gradient on buttons or cards.
- **Icons:** Lucide through the existing `lucide()` helper, 18px in navigation, 16px in buttons. No emoji.
- **Logos:** the logo files are PNG rasters held in the design system artifact, not in this repo (`docs/design-system/assets/Logos/README.md`). Keep using the app's current logo files until Jason supplies the masters.
- **Voice:** sentence case, short sentences, "you", hospital words (device, fault, clinic), buttons that say what happens.
- **Accessibility:** 44px touch targets on phones, 2px `primary` focus ring with 2px offset, labels on every field.

## 5. Screens

Mockups are in `screens/`. Routes and files come from the plan.

| Mockup | Route | What it shows |
| --- | --- | --- |
| `Join.dc.html` | `/join` | Account form: name, email, password, country, city, "I am a…", why join, contact consent, "Invited by". |
| `Start.dc.html` | `/community/start` | Applicant home: intro video, book the welcome meeting, the five quests with progress. |
| `Consent.dc.html` | `/community/welcome` | Ambassador welcome and the social media consent question. |
| `Journey.dc.html` | `/community` | My journey: current roles, next unlocks with progress, points level. |
| `Main.dc.html` | `/community/tree` | The skill tree: six paths, tiers, leads, Community team. |
| `Role.dc.html` | `/community/roles/{key}` | One role: what it does, requirements, what it unlocks, holders nearby. |
| `Unlock.dc.html` | after an unlock | The unlock moment with share link. |
| `Lead.dc.html` | lead view of `/community/admin/members` (phase 4) | City or country lead dashboard. |
| `AdminApplicants.dc.html` | `/community/admin/applicants` | Applicant list and detail: host, meeting time, notes, "Meeting held", "Refuse…". |
| `AdminMembers.dc.html` | `/community/admin/members` | Members with roles and counts, scoped for leads; add role and flag. |
| `AdminRoles.dc.html` | `/community/admin/roles/new` (1b) | Role editor: names in three languages, path, tier, scope, unlock mode, requirements, permissions. |
| `Home.dc.html` | `/home` | One app: grouped sidebar Work, Community, Admin; next unlock card; work and community cards. |
| `Profile.dc.html` | `/profile` | One profile: stats, community roles, clinic roles, achievements, LinkedIn share. |
| `Inbox.dc.html` | `/tasks` | Two tabs: My jobs and Community. |
| `Progress.dc.html` | fault detail | Progress toast after resolving a fault; locked actions with "Unlock as Repairer". |

Names, places and numbers in the mockups are examples.

## 6. Decisions that change the vault

These are newer than the vault and must be added to `07-decisions/decisions-log.en.md` as new rows (never edit an old row). Add them in the docs repo, not here.

| Decision | Replaces |
| --- | --- |
| Everyone joins through `/join`, which creates an account. The platform opens once the Ambassador quests are done (profile, intro video, welcome meeting confirmed by its host, Discord, consent). An engineer's invitation no longer skips this. | #15 |
| Clinic staff invited by a clinic watch a short staff video, then use their clinic. They do the other quests only to unlock more features. | #15 |
| Only Repairers order spare parts. | #18 |
| Community roles unlock app features and permissions; points unlock achievements and benefits (trainings, partner introductions, grants), as levels. Roles pause after 6 months without activity. | — |
| Makers make only non-critical parts by digital manufacturing (3D printing, laser cutting, CNC). Other parts are for Certified makers with quality control certificates. | — |

The vault copy used for this brief is from 2026-10-23. Before starting a phase, check the docs repo for newer notes.

## 7. Rules for the work

- Branch from `dev`, open the PR against `dev`. One PR per phase.
- New migration files only; never edit an applied one. Update `models/models.py` to match.
- Register every new page router in `frontend/main.py`.
- Refresh the `UserContextMiddleware` session keys when roles or status change.
- Escape JSON embedded in `<script>` like `_js_json` in `features/faults/pages/fault_list.py`.
- New env vars (`COMMUNITY_BOOKING_URL`, `COMMUNITY_INTRO_VIDEO_URL`, `STAFF_INTRO_VIDEO_URL`) go in `.env.example`, the compose files and the deploy workflow heredocs.
- No secrets in code, docs or commits. The Healthsites API key stays in the local `.env`.

## 8. Open questions to ask Jason, not guess

- Where the intro and staff videos are hosted (YouTube, Vimeo, MinIO). Until then, read the URLs from env vars.
- Whether community team admins stay superusers.
- Whether city-level roles are needed in phase 1.

## 9. Starter prompt

Paste this into Claude Code in the repo:

```
Read docs/implementation/community-journey/BRIEF.md, then the files it lists in section 1.
Build phase 1 of the community journey as described in docs/docs/community-journey.md.
Use the FixMyMedTech design system in docs/design-system/ for every screen, and the
mockups in docs/implementation/community-journey/screens/ for layout and copy.
Branch from dev. Start with the migration and utils/community.py with pytest tests,
then the gate, then the pages. Show me the plan before you write code, and stop
after each of these three steps so I can check it on the local stack.
```
