# FixMyMedTech 

> A platform that gives biomedical engineers the knowledge, tools, and community to diagnose, repair, and maintain medical equipment — anywhere on the continent.

**Fix My MedTech** is an open-source platform where biomedical engineers tag, track, diagnose, and repair medical devices. It is built around the realities of the field: devices that arrive without manuals, without spare
parts, and often already degraded — in environments where heat, humidity, dust and unstable power accelerate failure far beyond what manufacturers expect.

| Pillar | What it does |
|--------|--------------|
| **Tag & Map** | Register every device with a QR tag; clinics scan to report issues instantly; every device appears on a continent-wide map. |
| **Access Documentation** | User manuals, maintenance guides, schematics and diagrams gathered in one place — available offline. |
| **AI-Guided Repair** | An assistant that helps engineers navigate documentation, structure root-cause analysis, and find the right repair path. |
| **Source Spare Parts** | A virtual inventory connects engineers with available parts across clinics and suppliers — buy, sell, or trade within the network. |

Three pillars shape the project: **mapping** (the first structured, continent-wide
map of devices in the field), **repair** (a structured repair co-pilot, not a chatbot),
and **community** (open source, crowdsourced knowledge, engineers helping each
other across borders). The long-term vision is to move from repair hubs to
**manufacturing hubs** in every African country — assembling devices locally with
3D printing, CNC, laser cutting and PCB fabrication.

Built by and for biomedical engineers (Cameroon — Spain — Belgium). The platform
is free for engineers.

📚 **Full documentation:** <https://fixmymedtech.github.io/fixmymedtech-app/>

---

## Quick start

The fastest way to run the whole stack on your machine — PostgreSQL, MinIO,
backend and frontend — with no external accounts.

Clone the repo and copy configuration:

```bash
git clone <repo-url> && cd fixmymedtech-app

cp .env.example .env
```

Build and run the docker container:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

| Service | URL |
|---------|-----|
| App (FastHTML) | <http://localhost:5001> |
| API (FastAPI) + Swagger | <http://localhost:8888> · <http://localhost:8888/docs> |
| Admin portal (SQLAdmin) | <http://localhost:8888/admin/> |
| MinIO console | <http://localhost:9003> (`minioadmin` / `minioadmin`) |

Creating your first admin (optional — set `SUPERUSER_EMAIL` / `SUPERUSER_PASSWORD`
in the environment to have it done automatically on every startup):

```bash
docker compose -f docker-compose.local.yml exec backend python utils/create_superuser.py
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| API server | FastAPI (REST + reverse proxy hub + SQLAdmin admin portal) |
| Frontend | FastHTML (server-rendered HTML, no SPA / build step) |
| Auth | FastAPI-Users + JWT (server-side encrypted sessions) |
| Database | PostgreSQL (hosted on Supabase, or local container) |
| Object storage | MinIO (S3-compatible) — device photos |
| Photo processing | Pillow (compress) + rembg / Gemini API (white background) |
| Deployment | Docker Compose · GitHub Actions · nginx |
| Docs | MkDocs Material |

---

## Architecture

```
Browser (HTTPS)
   │
   ▼
nginx ──► Backend FastAPI  :8888          ← "proxy hub"
              ├─ serves  /admin   (SQLAdmin admin portal)
              ├─ serves  /api/*   (REST + auth)
              ├─ serves  /docs    (Swagger)
              └─ proxies the UI to FastHTML frontend (frontend:5001)
                              │   server-side httpx
                              ▼
                      FastAPI backend
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
      PostgreSQL (Supabase pooler)     MinIO (device photos)
```

FastHTML is not a traditional frontend — it is a Python web server that renders
HTML server-side. There is no JavaScript framework, no build step, and the
browser never calls the API directly. JWT tokens are stored in **encrypted
server-side sessions** (cookies) and never exposed to the browser.

---

## Device photos

Devices can carry photos of the equipment:

1. **Capture** — take a picture from the device form (browser camera) or upload a file.
2. **Compress** — the image is EXIF-corrected, downscaled to 1600 px and
   re-encoded as an optimized JPEG before being stored in MinIO.
3. **Process (async)** — the photo is re-processed on a background task to get a
   **pure white background** (local `rembg` U-Net model, or the Gemini
   "Nano Banana" API if `GEMINI_API_KEY` is set) and stored as a second object.
4. **Serve** — the detail page shows the white-background version when ready
   (`processed_…`), falling back to the original.

Turn processing off with `AUTO_PROCESS_PHOTO=off`.

---

## User roles

| Role | What they can do |
|------|-----------------|
| `superuser` | Full access, including the `/admin` SQLAdmin portal and user management |
| `admin` | Manage hospitals/orgs, devices and users |
| `technician` | Register devices, maintain equipment, log maintenance |
| `clinical_staff` / `engineering_staff` | Scan QR codes, view device info, report faults |

---

## Project structure

```
fixmymedtech-app/
│
├── backend/                        ← FastAPI REST API
│   ├── main.py                     ← App entry, CORS, routers, SQLAdmin, UI proxy
│   ├── admin_auth.py               ← SQLAdmin auth (superuser-only)
│   ├── migrations.py               ← Auto-applies SQL migrations on startup
│   ├── config/                     ← db_config, users, email, oauth, storage (MinIO)
│   ├── models/models.py            ← SQLAlchemy models
│   ├── routers/                    ← auth, devices, faults, maintenance, dashboard, orgs…
│   ├── utils/                      ← photo_processing, create_superuser…
│   └── requirements.txt
│
├── frontend/                       ← FastHTML frontend server (server-rendered UI)
│   ├── main.py                     ← App + page mounting
│   ├── config/api.py               ← Server-side httpx client → FastAPI
│   ├── features/                   ← auth, devices, dashboard, profile, tasks, groups…
│   └── requirements.txt
│
├── infrastructure/
│   ├── migrations/                 ← NNN_name.sql (applied in order, tracked)
│   ├── db/init.sql                 ← Base schema bootstrap (fresh local DB / new Supabase)
│   └── nginx/                      ← Sample vhost config for prod/dev servers
│
├── docker-compose.yml              ← Production stack (backend + frontend + minio)
├── docker-compose.dev.yml          ← Dev-server stack (backend + frontend + minio)
├── docker-compose.local.yml        ← Fully local stack (PostgreSQL + minio + app)
├── .env.example                    ← Environment template (all services)
└── docs/                           ← MkDocs source → GitHub Pages
```

There are three compose stacks:

| Compose file | PostgreSQL | Host ports (app / minio) | Used by |
|--------------|------------|--------------------------|---------|
| `docker-compose.local.yml` | local container | `8888` / `5001` / `9002–9003` | local development |
| `docker-compose.dev.yml` | Supabase (dev) | `8889` / `5002` / `9002–9003` | dev server (`/opt/fixmymedtech-dev`) |
| `docker-compose.yml` | Supabase (prod) | `8888` / `5001` / `9000–9001` | prod server (`/opt/fixmymedtech`) |

MinIO runs **per environment** (own container + volume), so dev and prod never
share objects.

---

## Database schema

There is no manual schema step:

- The backend creates the `fixmymedtech` schema and applies every migration from
  **`infrastructure/migrations/`** at startup, in filename order, tracked in
  `fixmymedtech.schema_migrations`.
- **`infrastructure/db/init.sql`** is the local one-time base-schema bootstrap
  (includes demo seed data). The local compose mounts it into a fresh PostgreSQL
  volume automatically. For a brand-new Supabase project there is no manual step:
  `000_initial_schema.sql` bootstraps the base tables on first backend boot.

---

## Deploy

- **Dev** — push to `dev` → GitHub Action deploys to `/opt/fixmymedtech-dev`
  (`docker-compose.dev.yml`).
- **Prod** — push to `main` → deploys to `/opt/fixmymedtech`
  (`docker-compose.yml`).
- Both support `workflow_dispatch` from the Actions tab.

Secrets live in GitHub environments (`DEV_*` / `PROD_*`), written to the server's
`.env` on each deploy. The nginx vhost proxies HTTPS to the backend port, which
requires trusting forwarded headers — the backend is started with
`--forwarded-allow-ips "*"` so the admin portal and link URLs are generated as
`https://…`.

An admin account can be created automatically on every deploy by setting
`DEV_SUPERUSER_EMAIL` / `DEV_SUPERUSER_PASSWORD` (and `PROD_*`) secrets — no
manual step on the server.

---

## Environment variables

See `.env.example` in the repo root for the complete set (DB, JWT, SMTP, OAuth,
MinIO, photo processing, superuser bootstrap). Highlights:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL asyncpg connection string |
| `DB_SCHEMA` | App schema (default `fixmymedtech`) |
| `AUTH_JWT_SECRET` | JWT signing secret (≥ 32 bytes) |
| `FRONTEND_URL` / `API_URL` | Public URL and internal backend URL |
| `MINIO_ENDPOINT` / `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` / `MINIO_BUCKET` | Object storage |
| `AUTO_PROCESS_PHOTO` / `GEMINI_API_KEY` / `PHOTO_MAX_DIMENSION` / `PHOTO_JPEG_QUALITY` | Device photo pipeline |
| `SUPERUSER_EMAIL` / `SUPERUSER_PASSWORD` / `SUPERUSER_NAME` | Auto-create admin on startup |
| `MAIL_SERVER` … / `GOOGLE_CLIENT_ID` … | SMTP email + OAuth login (optional) |

---

## QR codes

Each device gets a permanent public URL that requires no login:

```
https://{your-domain}/d/{device_id}
```

Scanning the QR opens the device page: specs, documentation, fault reporting and
maintenance history. The UUID never changes; the content behind it is always live.

---

## Community

- **Documentation:** <https://fixmymedtech.github.io/fixmymedtech-app/>
- **Source:** <https://github.com/FixMyMedTech/fixmymedtech-app>
- Built with ❤️ for biomedical engineers across the continent.