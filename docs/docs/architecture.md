# FixMyMedTech — Architecture Guide

Medical equipment management platform for LMICs (Low and Middle Income Countries).

**Stack:** FastAPI (REST API, auth, admin portal, reverse proxy) + FastHTML
(server-rendered UI) + PostgreSQL + MinIO (object storage).

---

## Architecture overview

```
Browser (HTTPS)
   │
   ▼
nginx ──► Backend FastAPI  :8888          ← single public entry point
              ├─ /api/*     REST API + auth
              ├─ /admin     SQLAdmin portal (superusers only)
              ├─ /docs      Swagger
              ├─ /health
              └─ /{path}    reverse proxy → FastHTML frontend (frontend:5001)
                                │  server-side httpx, Bearer token
                                ▼
                         Backend /api/*
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
   PostgreSQL (local or Supabase)        MinIO (device / fault / avatar photos)
```

FastHTML is not a traditional frontend — it is a Python web server that renders
HTML server-side. There is no JavaScript framework and no build step. The
browser never calls the API directly: it talks to FastHTML (through the backend
proxy), and FastHTML calls the API server-side.

### The backend as proxy hub

Every request reaches the FastAPI backend first. The catch-all route in
`backend/main.py` forwards anything that is not `admin`, `docs`, `redoc`,
`openapi.json`, `health` or `api/*` to `http://frontend:5001`, adding
`X-Forwarded-Host` / `X-Forwarded-Proto` so the frontend can build correct
absolute URLs (e.g. device QR links). The backend runs with
`--forwarded-allow-ips "*"` so URLs behind nginx are generated as `https://…`.

---

## Project structure

```
fixmymedtech-app/
│
├── backend/                        ← FastAPI REST API
│   ├── main.py                     ← App entry, CORS, routers, SQLAdmin views, UI proxy
│   ├── admin_auth.py               ← SQLAdmin login (superuser-only)
│   ├── migrations.py               ← Applies infrastructure/migrations/*.sql on startup
│   ├── config/                     ← db_config, users (FastAPI-Users/JWT), email, oauth, storage (MinIO)
│   ├── models/models.py            ← SQLAlchemy models
│   ├── routers/                    ← auth, profile, oauth, devices, fault_reports,
│   │                                  maintenance_logs, dashboard, organizations,
│   │                                  healthsites, admin_email
│   ├── utils/                      ← profile deps, photo_processing, create_superuser, username
│   └── templates/                  ← Email + SQLAdmin templates
│
├── frontend/                       ← FastHTML server
│   ├── main.py                     ← App setup, middleware, mounts each feature router
│   ├── config/api.py               ← httpx helpers (_get/_post/_patch/_delete) → backend
│   ├── components.py               ← Page shells, sidebar, badges, map, QR scanner, CSS
│   ├── i18n.py                     ← Translations (en / es / fr)
│   └── features/<feature>/         ← auth, dashboard, devices, faults, maintenance,
│       ├── api.py                     groups, network, profile, tasks, home
│       └── pages/*.py
│
├── infrastructure/
│   ├── migrations/                 ← NNN_name.sql, applied in order, tracked
│   └── db/init.sql                 ← Base schema for a fresh local PostgreSQL volume
│
├── scripts/                        ← seed_test_data.py, generate_qr.py, setup_local_db.sh
├── docker-compose.local.yml        ← Local stack (PostgreSQL + MinIO + backend + frontend)
├── docker-compose.dev.yml          ← Dev server (Supabase dev + MinIO)
├── docker-compose.yml              ← Production (Supabase prod + MinIO)
└── docs/                           ← This MkDocs site
```

### Frontend feature pattern

Each feature in `frontend/features/<feature>/` contains:

- `api.py` — thin async wrappers over backend endpoints, built on the helpers
  in `config/api.py`. Errors are raised as `httpx.HTTPStatusError` carrying the
  backend's `detail` message.
- `pages/*.py` (or `pages.py`) — each module defines `rt = APIRouter()` and its
  route handlers, rendering with the shells from `components.py`
  (`page_shell` for logged-in pages, `pub_shell` for public QR pages,
  `auth_shell` for login/signup).

Every page router is registered in `frontend/main.py` with
`module.rt.to_app(app)`. Registration order matters when patterns overlap
(e.g. `/profile/photo` must be registered before `/profile/{profile_id}`).

All user-visible text goes through `i18n.py`: `_ = t(lang)` then `_("key")`,
with `lang` taken from the session (switchable via `POST /lang`).

---

## Key design decisions

### Why two servers?

FastHTML handles routing and rendering; FastAPI handles data and business logic.

- The API can be used independently by mobile apps or third parties later.
- Authorization and business rules live in one place (the API).
- FastHTML stays thin — it fetches data and renders HTML.

### Authentication

- Accounts are local, managed by **FastAPI-Users** (`backend/config/users.py`)
  with JWT bearer tokens signed with `AUTH_JWT_SECRET`. Optional Google /
  GitHub / Discord OAuth is configured in `backend/config/oauth.py`.
- On login, FastHTML stores the JWT in its session cookie
  (`req.session["token"]`, signed with `SESSION_SECRET`) and sends it as an
  `Authorization: Bearer` header on every server-side API call. The browser
  never sends API requests itself.
- Protected endpoints use `Depends(get_current_profile)`
  (`backend/utils/profile.py`), which loads the caller's `Profile` together
  with their organization memberships. Public endpoints use
  `get_optional_profile` or no dependency at all.
- The `/admin` SQLAdmin portal has its own session login restricted to users
  with `is_superuser = true`.

### Organizations and roles

Users belong to one or more **organizations** through `org_users`, and the role
is **per organization**:

| Role | What they can do |
|------|-----------------|
| `superuser` (account flag) | Everything, including the `/admin` portal |
| `admin` | Manage the organization, its members, devices; assign and approve faults |
| `technician` | Register devices, diagnose/repair faults, log maintenance |
| `engineering_staff` | Like technician; can be assigned faults |
| `clinical_staff` | Scan QR codes, view device info, report faults |

A device is linked to **two** organizations:

- `organization_maintenance_id` — the organization that maintains it
  (receives its fault reports);
- `healthsite_id` — the hospital/clinic where it is installed (approves repair
  quotes).

### Fault workflow

Fault reports move through steps, each performed by a different person
(see the header of `backend/routers/fault_reports.py`):

```
open ──(maintenance-org admin assigns)──► assigned
     ──(assignee: diagnosis + quote)────► diagnosed
     ──(healthsite admin approves)──────► approved      (rejection → back to assigned)
     ──(assignee repairs, final price)──► resolved
```

`in_progress` is an optional step when the assignee goes on site. A device
without a healthsite is approved by the maintenance-org admin.

### Document library

Manuals and guides live in `fixmymedtech.documents`, and devices link to them
through `device_documents` (many to many), so one manual serves every device
of that model. A document is either:

- **from iFixit** (`source = 'ifixit'`): a *link* to a PDF in the iFixit
  library, found by manufacturer and model. The file is never copied; the row
  stores the URL and iFixit ids, once per iFixit document. Metadata always
  comes from iFixit itself (`backend/config/ifixit.py`, cached for a day).
- **uploaded** (`source = 'upload'`): a PDF stored in MinIO. Uploads start
  with `contribution_status = 'pending'`; sending them to the iFixit library
  after a superuser's approval is planned.

Anyone can read documents (device page, public QR page, `/library`).
Attaching, uploading and removing need a logged-in user. Uploads are limited
to PDFs of `DOCUMENT_MAX_MB` (50 MB by default); the nginx `client_max_body_size`
in front of the app must allow that size.

### Feedback button

Every page shows a **?** button (bottom-right) with two choices, *Send feedback*
and *Report an issue*. Both open the `/feedback` form, which works with or
without login. `POST /api/feedback/` stores the report in
`fixmymedtech.feedback` first, then posts it in the background to a Discord
forum channel through a webhook, creating one thread per report
(`backend/config/discord.py`). The outcome is recorded in `discord_status`
(`sent`, `failed`, or `disabled` when no webhook is configured), and every
report is visible in the admin portal under **Feedback**. Email addresses are
never posted to Discord.

### Device photos

Uploads are EXIF-corrected, downscaled and re-encoded as JPEG (Pillow), then
stored in MinIO. A background task produces a white-background variant (local
`rembg`, or Gemini if `GEMINI_API_KEY` is set). Disable it with
`AUTO_PROCESS_PHOTO=off`.

---

## Page map

| URL | Auth | What |
|-----|------|------|
| `/login`, `/signup`, `/forgot-password`, `/reset-password` | No | Account pages |
| `/d/{id}` | **No** | Public device page (QR target) |
| `/d/{id}/report` | **No** | Report a fault |
| `/d/{id}/fault/{fault_id}`, `/d/{id}/log/{log_id}` | **No** | Public fault / maintenance log view |
| `/home` | Yes | Landing page with QR scanner |
| `/dashboard` | Yes | Stats overview |
| `/devices`, `/new_device` | Yes | Device list, register device |
| `/device/{id}` | Yes | Device detail, faults, maintenance history |
| `/devices/{id}/edit` | Yes | Edit device |
| `/faults` | Yes | Fault queue for the organizations you maintain for |
| `/tasks` | Yes | Faults and maintenance logs assigned to you |
| `/groups`, `/groups/{org_id}` | Yes | Organizations, members, join requests |
| `/network` | Yes | Directory of other professionals |
| `/profile`, `/profile/{profile_id}` | Yes | Your profile, other profiles |

---

## Data flow — QR scan (no login)

```
1. Nurse scans the QR on a device
2. Browser opens https://{domain}/d/{device_id}  (backend proxies to FastHTML)
3. FastHTML calls GET {API_URL}/api/devices/public/{device_id}
4. FastAPI reads PostgreSQL (no auth required for this endpoint)
5. FastHTML renders device info, documentation and the fault report form
6. Nurse submits → FastHTML calls POST /api/faults/public
7. FastAPI stores the report; a high/critical severity sets the device status to "fault"
```

## Data flow — login

```
1. User submits the login form
2. FastHTML calls POST {API_URL}/api/auth/login
3. FastAPI-Users verifies the password and returns a JWT
4. FastHTML stores the JWT in its session cookie
5. Each later page fetches data server-side with Authorization: Bearer <jwt>
6. FastAPI validates it on every protected endpoint via Depends(get_current_profile)
```

---

## Database

All tables live in the `fixmymedtech` schema. Migrations in
`infrastructure/migrations/` are applied automatically at backend startup, in
filename order, and tracked in `fixmymedtech.schema_migrations`. See
[Database Schema](database.md) for the tables.

---

## Environments and deploy

| Compose file | PostgreSQL | Host ports (api / app / minio) | Used by |
|--------------|------------|--------------------------------|---------|
| `docker-compose.local.yml` | local container | `8888` / `5001` / `9002–9003` | local development |
| `docker-compose.dev.yml` | Supabase (dev) | `8889` / `5002` / `9002–9003` | dev server |
| `docker-compose.yml` | Supabase (prod) | `8888` / `5001` / `9000–9001` | prod server |

- Push to `dev` → GitHub Actions deploys to `/opt/fixmymedtech-dev`.
- Push to `main` → deploys to `/opt/fixmymedtech`.

Secrets live in the GitHub `development` / `production` environments and are
written to the server's `.env` on each deploy. See
[Getting Started](getting_started.md) for the environment variable reference.
