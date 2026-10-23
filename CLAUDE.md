# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FixMyMedTech: a platform for biomedical engineers to tag (QR), track, report faults on, and maintain medical devices. Python only: a FastAPI backend and a FastHTML server-rendered frontend. There is no JS build step and no SPA.

## Commands

The full local stack (PostgreSQL, MinIO, backend, frontend):

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up --build -d
docker compose -f docker-compose.local.yml logs -f backend   # or frontend
docker compose -f docker-compose.local.yml exec backend python utils/create_superuser.py
python scripts/seed_test_data.py        # test orgs/users (all passwords Pass123!), targets localhost:5432
```

Source isn't volume-mounted into the containers, so code changes need `up --build`.

- App: http://localhost:5001 (also reachable through the backend at :8888)
- API + Swagger: http://localhost:8888/docs
- SQLAdmin: http://localhost:8888/admin/ (superusers only)
- MinIO console: http://localhost:9003

To run outside Docker: `cd backend && uvicorn main:app --reload --port 8888` and `cd frontend && python main.py` (FastHTML `serve()` with live reload). The frontend reads `API_URL` (default `http://localhost:8888`).

Docs: `cd docs && mkdocs serve`.

The repo has no test suite and no linter config.

## Architecture

### Request flow

```
Browser → (nginx) → backend FastAPI :8888
                       ├─ /api/*     REST (routers/)
                       ├─ /admin     SQLAdmin
                       ├─ /docs, /health
                       └─ /{path}    catch-all reverse proxy → http://frontend:5001
                                         │ server-side httpx with Bearer token
                                         ▼
                                    backend /api/*  → PostgreSQL + MinIO
```

- The backend is the public entry point. Its catch-all `proxy` route in `backend/main.py` forwards everything that isn't `admin|docs|openapi.json|redoc|health|api*` to the FastHTML container, and it sets the `X-Forwarded-Host`/`X-Forwarded-Proto` headers that the frontend uses to build absolute URLs (QR links).
- The browser never calls the API directly. The frontend keeps the JWT in its session cookie (`req.session["token"]`, which is signed with `SESSION_SECRET` but not encrypted) and calls the backend server-side.

### Backend (`backend/`)

- `main.py`: wires up the routers, defines SQLAdmin `ModelView`s (creating a `UserAdmin` user also creates a Profile and a default org, then emails an invite), and holds the proxy.
- Auth uses FastAPI-Users with JWT (`config/users.py`). Routers resolve the caller with `utils/profile.py` → `get_current_profile` / `get_optional_profile`. Public (no-login) endpoints live under `/public/...` paths, e.g. `/api/devices/public/{id}` and `/api/faults/public`.
- Models are in `models/models.py` (SQLAlchemy async, every table in schema `DB_SCHEMA`, default `fixmymedtech`). Key relationships:
  - `User` 1:1 `Profile` (shared id).
  - `Profile` ↔ `Organization` through `OrgUser`, which carries a per-org `role`: admin / technician / engineering_staff / clinical_staff.
  - A `Device` has two org links: `organization_maintenance_id` (the org that maintains it) and `healthsite_id` (the hospital it sits in). Authorization often depends on which of the two orgs the caller belongs to.
- Serialization pitfall (see the header of `routers/fault_reports.py`): `Profile.user` is `lazy="selectin"`, so returning ORM rows can leak `hashed_password`. Build response dicts by hand from columns.
- The fault workflow is a multi-step state machine documented at the top of `routers/fault_reports.py` (open → assigned → diagnosed → approved → resolved). Each step has its own endpoint and authorization rule.
- Photos are compressed with Pillow and stored in MinIO (`config/storage.py`). A background task then makes a white-background variant (`utils/photo_processing.py`, using rembg or Gemini; disable it with `AUTO_PROCESS_PHOTO=off`).

### Database migrations

- Schema changes go in a new `infrastructure/migrations/NNN_name.sql`. On startup the backend applies every pending file in filename order (`backend/migrations.py`) and records it in `fixmymedtech.schema_migrations`. Each file runs exactly once, so never edit an applied migration; add a new one instead.
- `infrastructure/db/init.sql` bootstraps only a fresh local Postgres volume. `000_initial_schema.sql` does the same job for a fresh Supabase database.
- Also update `models/models.py` to match.

### Frontend (`frontend/`)

- `features/<feature>/` follows one pattern:
  - `api.py` wraps the backend endpoints with the `_get/_post/_patch/_delete` helpers from `config/api.py`. These raise `httpx.HTTPStatusError` and carry the backend's `detail`.
  - `pages/*.py` (or `pages.py`) each define `rt = APIRouter()` plus FastHTML route handlers.
- Every page router must be registered in `frontend/main.py` with `xxx.rt.to_app(app)`. Order matters where paths overlap: `my_profile` has to come before `profile_detail`.
- `components.py` holds the shared UI: `page_shell` (authenticated pages), `pub_shell` (public QR pages), `auth_shell`, `status_badge`, `map_component`, `qr_scanner_component`, and so on. Any inline JS lives as Python strings inside the page modules.
- i18n: every user-visible string is a key in `i18n.py` `STRINGS` for `en`, `es` and `fr`. In a page, get the translator with `_ = t(lang)` and call `_("key")`. The language comes from `req.session["lang"]`. When you add a string, add it to all three languages.
- `features/auth/helper.py` provides the session/token helpers. `UserContextMiddleware` in `main.py` caches `/api/auth/me` in the session for the avatar menu, so refresh those session keys whenever the profile changes.
- When you embed JSON in a `<script>`, escape it the way `_js_json` in `features/faults/pages/fault_list.py` does.

### Deployment

- There are three compose files: `docker-compose.local.yml` (local Postgres), `docker-compose.dev.yml` (Supabase dev, ports 8889/5002), and `docker-compose.yml` (prod).
- GitHub Actions deploy over SSH:
  - Pushing `dev` deploys to `/opt/fixmymedtech-dev`.
  - Pushing `main` deploys to production at `/opt/fixmymedtech`.
  - Secrets are written into the server's `.env` on each deploy. A new env var has to be added to the workflow's `.env` heredoc and to the matching compose file.
- Contribution flow: branch from `dev` and open PRs against `dev`. Maintainers merge `dev` into `main`.


