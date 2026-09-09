# Getting Started — Developer Guide

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose V2)
- **Git**
- A **Supabase** project (free tier works) — or any PostgreSQL database
- (Optional) Python 3.12 + `uv` / `pip` if you want to run services outside Docker

---

## 1. Clone and configure

```bash
git clone <repo-url> && cd fixmymedtech-app

cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to find it |
|----------|------------------|
| `DATABASE_URL` | Postgres connection string (Supabase pooler or local). `postgresql+asyncpg://…` |
| `DB_SCHEMA` | `fixmymedtech` (default) |
| `FRONTEND_URL` | `http://localhost:8888` for local dev |

### Optional (for OAuth / email)

```env
# OAuth (leave blank to disable the buttons)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# SMTP (leave MAIL_SERVER blank to log emails to console instead)
MAIL_SERVER=
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=noreply@fixmymedtech.org

# JWT signing secret (change in production)
AUTH_JWT_SECRET=replace-with-a-random-string
```

---

## 2. Start with Docker (recommended)

### Option A — Local stack (PostgreSQL + MinIO, no account needed)

Recommended for day-to-day development. Runs the whole app against a local
PostgreSQL container, no Supabase project required:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

This builds and starts four containers:

| Service   | URL | What it does |
|-----------|-----|--------------|
| **db**       | `localhost:5432` | PostgreSQL 16 (isolated `pg-data` volume) |
| **minio**    | console `http://localhost:9003` | S3-compatible file storage |
| **backend**  | `http://localhost:8888` | FastAPI REST API |
| **frontend** | `http://localhost:5001` | FastHTML server-side UI |

On first boot the database is initialised from `infrastructure/db/init.sql`, then the backend
auto-applies every migration in `infrastructure/migrations/` in order.

> The local stack uses its own compose project (`fixmymedtech-local`), so its
> `pg-data` / `minio-data` volumes and host ports are independent of Option B
> below — switch between them freely without losing data.

### Option B — Supabase / remote PostgreSQL

If you prefer to develop against your Supabase project, set `DATABASE_URL` in
`.env` (see section 1) and run:

```bash
docker compose up --build -d
```

This builds and starts two containers:

| Service | URL | What it does |
|---------|-----|--------------|
| **backend** | `http://localhost:8888` | FastAPI REST API |
| **frontend** | `http://localhost:5001` | FastHTML server-side UI |

Once running:

- **App:** <http://localhost:5001>
- **API docs (Swagger):** <http://localhost:8888/docs>
- **Admin portal:** <http://localhost:8888/admin/> *(superuser only — see below)*
- **MinIO console:** <http://localhost:9003> *(Option A only — creds `minioadmin`/`minioadmin`)*

### First-time setup — create a superuser

After the containers are up, create your first admin account:

```bash
docker compose exec backend python utils/create_superuser.py
```

(With the local stack, add `-f docker-compose.local.yml`: `docker compose -f docker-compose.local.yml exec backend python utils/create_superuser.py`)

The script asks for email, name, and password interactively. It creates
the user (with profile + default org) and marks them as superuser.

To promote an existing user to superuser, run the script with their email — it
will update their password and grant superuser access.

**Automated (recommended for servers/deploys):** instead set `SUPERUSER_EMAIL`,
`SUPERUSER_PASSWORD` (and optional `SUPERUSER_NAME`) in your environment — the
backend then creates/promotes that admin automatically on every startup, right
after applying migrations. The dev/prod deploy workflows already pass these
through from the `DEV_SUPERUSER_*` / `PROD_SUPERUSER_*` GitHub secrets.

### Send invitations & verification emails

Once logged in as a superuser at `/admin/`:

| Feature | Where | What it does |
|---------|-------|--------------|
| **Invite a user** | `/admin-panel/invite` | Creates an account and sends a verification email with a link to set their password |
| **Resend verification** | User detail page → "Send Verification Email" button | Re-sends the verification email to an unverified user |
| **Password reset** | User detail page → "Send Password Reset" button | Sends a password reset link to the user |

> **Note:** When `MAIL_SERVER` is not configured (default for local dev), emails are logged to the backend console instead of being sent. Check `docker compose logs backend` to see the email content and verification links.

---

## 3. Project structure

```
fixmymedtech-app1/
├── backend/                          ← FastAPI REST API
│   ├── main.py                       ← App entry, CORS, router registration, SQLAdmin
│   ├── admin_auth.py                 ← SQLAdmin auth (superuser-only login)
│   ├── migrations.py                 ← Auto-runs SQL migration files on startup
│   ├── config/
│   │   ├── db_config.py               ← DB engine + async session factory
│   │   ├── users.py                  ← FastAPI-Users: UserManager, JWT backend, deps
│   │   ├── email.py                  ← fastapi-mail config (SMTP or console fallback)
│   │   └── oauth.py                  ← Authlib OAuth client (Google/GitHub)
│   ├── models/
│   │   └── models.py                 ← SQLAlchemy models (User, Profile, Device, …)
│   ├── routers/
│   │   ├── auth.py                   ← /api/auth/* (login, signup, me, tasks, …)
│   │   ├── oauth.py                  ← /api/auth/oauth/{provider} (social login)
│   │   ├── devices.py                ← /api/devices/*
│   │   ├── fault_reports.py          ← /api/faults/*
│   │   ├── maintenance_logs.py       ← /api/maintenance-logs/*
│   │   ├── dashboard.py              ← /api/dashboard/*
│   │   └── organizations.py          ← /api/organizations/*
│   ├── utils/
│   │   ├── profile.py                ← get_current_profile dependency
│   │   └── username.py               ← Auto-generate unique usernames
│   └── requirements.txt
│
├── frontend/                         ← FastHTML frontend server
│   ├── main.py                       ← All routes and page rendering
│   ├── components.py                 ← Reusable HTML components + CSS
│   ├── i18n.py                       ← Translations (EN/ES/FR)
│   ├── countries.py                  ← Country list
│   ├── features/
│   │   └── auth/                     ← Login, signup pages + API helpers
│   ├── config/
│   │   └── api.py                    ← HTTP client (calls FastAPI via httpx)
│   ├── static/                       ← Images, favicon
│   └── requirements.txt
│
├── infrastructure/
│   └── migrations/                   ← SQL migrations (run in order on startup)
│       ├── 001_device_coordinates.sql
│       ├── …
│       ├── 011_local_auth_users.sql  ← Creates local users table
│       └── 012_fastapi_users.sql     ← Aligns schema for FastAPI-Users
│
├── docker-compose.yml                ← Production compose (backend + frontend)
├── docker-compose.dev.yml            ← Dev-server compose (backend + frontend + minio)
├── docker-compose.local.yml          ← Local dev stack (PostgreSQL + minio + backend + frontend)
├── .env.example                      ← Template for environment variables
└── README.md                         ← Architecture overview
```

---

## 5. Admin portal

The admin portal at `/admin/` uses [SQLAdmin](https://aminaltay.dev/sqladmin/) to provide a browsable database UI.

**Who can access:** Only users with `is_superuser = true` in the `fixmymedtech.users` table.

**Available models:**

| Model | What it shows |
|-------|---------------|
| Users | Auth accounts (email, is_active, is_verified, is_superuser) |
| Profiles | User profiles (username, full_name) |
| Org Users | User↔Organization links and roles |
| Organizations | Hospitals, clinics, etc. |
| Device Categories | Equipment categories (seeded from CSV) |
| Devices | All registered equipment |
| Documents | Manuals, guides, videos linked to devices |
| Fault Reports | Submitted fault reports |
| Maintenance Logs | Maintenance history |

---

## 6. Database migrations

Migrations live in `infrastructure/migrations/` and are named `NNN_description.sql`. They run **automatically** on backend startup in numeric order. Each migration is recorded in `fixmymedtech.schema_migrations` so it only runs once.

To add a new migration:

```bash
# Pick the next number
cat > infrastructure/migrations/013_my_change.sql << 'SQL'
ALTER TABLE fixmymedtech.devices ADD COLUMN IF NOT EXISTS warranty_end DATE;
SQL
```

Restart the backend container and it will apply automatically.

---

## 7. Common tasks

### Create a new API endpoint

1. Add your route in the relevant `backend/routers/*.py` file
2. Use `Depends(current_active_user)` for auth, or `Depends(get_current_profile)` for profile + org context
3. Register the router in `backend/main.py` if it's a new file

### Add a new database model

1. Define the model in `backend/models/models.py`
2. Create a migration SQL in `infrastructure/migrations/`
3. Add a `ModelView` in `backend/main.py` for the admin portal

### Run a one-off DB query

```bash
docker compose exec backend python -c "
import asyncio
from config.db_config import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT count(*) FROM fixmymedtech.users'))
        print('Users:', result.scalar())

asyncio.run(main())
"
```

### View backend logs

```bash
docker compose logs -f backend
```

### Rebuild after dependency changes

```bash
docker compose up --build -d backend
```

---

## 8. Environment variables reference

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (asyncpg) |
| `DB_SCHEMA` | No | `fixmymedtech` | Database schema name |
| `FRONTEND_URL` | No | `http://localhost` | For CORS + email links |
| `AUTH_JWT_SECRET` | No | `dev-local-jwt-secret-change-me` | JWT signing secret |
| `AUTH_TOKEN_TTL` | No | `604800` (7 days) | JWT lifetime in seconds |
| `AUTH_SESSION_SECRET` | No | `dev-admin-session-secret` | Session cookie signing |
| `MAIL_SERVER` | No | *(empty — logs emails)* | SMTP host |
| `MAIL_PORT` | No | `587` | SMTP port |
| `MAIL_USERNAME` | No | — | SMTP login |
| `MAIL_PASSWORD` | No | — | SMTP password |
| `MAIL_FROM` | No | `noreply@fixmymedtech.org` | Sender address |
| `GOOGLE_CLIENT_ID` | No | — | OAuth (disables button if empty) |
| `GOOGLE_CLIENT_SECRET` | No | — | OAuth |
| `GITHUB_CLIENT_ID` | No | — | OAuth |
| `GITHUB_CLIENT_SECRET` | No | — | OAuth |

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | No | `http://backend:8888` | FastAPI backend URL |

---

## 9. Tech stack summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API server | FastAPI | REST endpoints, auth, business logic |
| Auth | FastAPI-Users 15 + JWT | Local user management, JWT tokens |
| Email | fastapi-mail | Verification, welcome, password reset |
| OAuth | Authlib | Google/GitHub social login |
| Admin UI | SQLAdmin | Browsable database portal (superuser only) |
| Frontend | FastHTML | Server-side HTML rendering |
| Database | PostgreSQL (Supabase) | Data storage |
| ORM | SQLAlchemy 2 (async) | Query builder |
| Migrations | Custom (file-based) | Auto-applied on startup |
| Containerization | Docker Compose | Multi-service orchestration |
