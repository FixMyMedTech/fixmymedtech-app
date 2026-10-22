# Getting Started — Developer Guide

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose V2)
- **Git**
- Nothing else for the local stack. Optionally, a **Supabase** project (or any PostgreSQL database) if you want to develop against a remote database
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

This builds and starts three containers:

| Service | URL | What it does |
|---------|-----|--------------|
| **backend** | `http://localhost:8888` | FastAPI REST API |
| **frontend** | `http://localhost:5001` | FastHTML server-side UI |
| **minio** | console `http://localhost:9001` | S3-compatible file storage |

Once running:

- **App:** <http://localhost:5001>
- **API docs (Swagger):** <http://localhost:8888/docs>
- **Admin portal:** <http://localhost:8888/admin/> *(superuser only — see below)*
- **MinIO console:** <http://localhost:9003> with Option A, <http://localhost:9001> with Option B *(creds `minioadmin`/`minioadmin` unless overridden)*

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

See [Architecture](architecture.md) for the full layout, request flow, and the
frontend feature pattern.

---

## 4. Admin portal

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

## 5. Database migrations

Migrations live in `infrastructure/migrations/` and are named `NNN_description.sql`. They run **automatically** on backend startup in numeric order. Each migration is recorded in `fixmymedtech.schema_migrations` so it only runs once.

To add a new migration:

```bash
# Pick the next number after the highest existing file
cat > infrastructure/migrations/026_my_change.sql << 'SQL'
ALTER TABLE fixmymedtech.devices ADD COLUMN IF NOT EXISTS warranty_end DATE;
SQL
```

Rebuild and restart the backend container (`up --build -d backend`) and it will apply automatically. Never edit a migration that has already been applied; add a new one. Update `backend/models/models.py` to match.

---

## 6. Common tasks

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

## 7. Environment variables reference

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (asyncpg) |
| `DB_SCHEMA` | No | `fixmymedtech` | Database schema name |
| `FRONTEND_URL` | No | `http://localhost` | For CORS + email links |
| `AUTH_JWT_SECRET` | No | `dev-local-jwt-secret-change-me` | JWT signing secret |
| `AUTH_TOKEN_TTL` | No | `604800` (7 days) | JWT lifetime in seconds |
| `AUTH_SESSION_SECRET` | Dev/prod | `dev-local-admin-session-secret` (local compose) | Signs the `/admin` login session. The dev and prod compose files refuse to start without it |
| `MAIL_SERVER` | No | *(empty — logs emails)* | SMTP host |
| `MAIL_PORT` | No | `587` | SMTP port |
| `MAIL_USERNAME` | No | — | SMTP login |
| `MAIL_PASSWORD` | No | — | SMTP password |
| `MAIL_FROM` | No | `noreply@fixmymedtech.org` | Sender address |
| `GOOGLE_CLIENT_ID` | No | — | OAuth (disables button if empty) |
| `GOOGLE_CLIENT_SECRET` | No | — | OAuth |
| `GITHUB_CLIENT_ID` | No | — | OAuth |
| `GITHUB_CLIENT_SECRET` | No | — | OAuth |
| `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` | No | — | OAuth |
| `MINIO_ENDPOINT` | No | `minio:9000` | MinIO host:port as seen from the backend |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | No | `minioadmin` | MinIO credentials |
| `MINIO_BUCKET` | No | `fixmymedtech` | Bucket for photos |
| `AUTO_PROCESS_PHOTO` | No | `on` | White-background photo processing (`off` to disable) |
| `GEMINI_API_KEY` | No | — | Use Gemini instead of local `rembg` for photo processing |
| `PHOTO_MAX_DIMENSION` / `PHOTO_JPEG_QUALITY` | No | `1600` / `85` | Photo compression |
| `HEALTHSITES_API_KEY` | No | — | healthsites.io lookup when registering organizations |
| `SUPERUSER_EMAIL` / `SUPERUSER_PASSWORD` / `SUPERUSER_NAME` | No | — | Auto-create a superuser on startup |

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | No | `http://localhost:8888` (compose sets `http://backend:8888`) | FastAPI backend URL |
| `SESSION_SECRET` | Dev/prod | `dev-local-session-secret` (local compose) | Signs the session cookie, which holds the user's JWT. The dev and prod compose files refuse to start without it |

---

## 8. Tech stack summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API server | FastAPI | REST endpoints, auth, business logic |
| Auth | FastAPI-Users 15 + JWT | Local user management, JWT tokens |
| Email | fastapi-mail | Verification, welcome, password reset |
| OAuth | Authlib | Google/GitHub social login |
| Admin UI | SQLAdmin | Browsable database portal (superuser only) |
| Frontend | FastHTML | Server-side HTML rendering |
| Database | PostgreSQL (local container or Supabase) | Data storage |
| Object storage | MinIO | Device, fault and avatar photos |
| ORM | SQLAlchemy 2 (async) | Query builder |
| Migrations | Custom (file-based) | Auto-applied on startup |
| Containerization | Docker Compose | Multi-service orchestration |
