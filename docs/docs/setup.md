# FixMyMedTech — Running Without Docker

The recommended way to develop is the Docker stack described in
[Getting Started](getting_started.md). This page covers running the backend and
frontend directly on your machine, which gives faster reloads while you edit
Python code.

---

## 1. Start the infrastructure

The backend needs PostgreSQL and MinIO. The easiest option is to start only
those two containers from the local stack:

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up -d db minio
```

This exposes PostgreSQL on `localhost:5432` (user/password `postgres`,
database `fixmymedtech`) and MinIO on `localhost:9002` (console on
`localhost:9003`, `minioadmin` / `minioadmin`).

A fresh PostgreSQL volume is initialised from `infrastructure/db/init.sql`.
You can also point `DATABASE_URL` at a Supabase project instead. In that case
the schema is created by the migrations on the first backend start.

---

## 2. Backend (FastAPI)

Requires Python 3.12.

```bash
cd backend
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fixmymedtech
export DB_SCHEMA=fixmymedtech
export MINIO_ENDPOINT=localhost:9002
export MIGRATIONS_DIR=../infrastructure/migrations

uvicorn main:app --reload --port 8888
```

- API: <http://localhost:8888/api/...>
- Swagger: <http://localhost:8888/docs>
- Admin portal: <http://localhost:8888/admin/>

Pending migrations are applied on startup. `MIGRATIONS_DIR` must point to
`infrastructure/migrations` relative to where you run the backend. The default
is `infrastructure/migrations`, which matches the Docker image layout.

Create a superuser with `python utils/create_superuser.py`, or set
`SUPERUSER_EMAIL` / `SUPERUSER_PASSWORD` before starting.

---

## 3. Frontend (FastHTML)

```bash
cd frontend
pip install -r requirements.txt

export API_URL=http://localhost:8888
export SESSION_SECRET=any-random-string

python main.py
```

The app runs at <http://localhost:5001> with live reload.

> Outside Docker, open the frontend directly on port 5001. The backend's UI
> proxy forwards to the hostname `frontend:5001`, which only resolves inside
> the compose network, so `http://localhost:8888/` will not show the app.

---

## 4. Seed test data (optional)

```bash
python scripts/seed_test_data.py
```

This creates demo organizations and users (all with password `Pass123!`) in
the database at `DATABASE_URL`, which defaults to
`postgresql+asyncpg://postgres:postgres@localhost:5432/fixmymedtech`.

---

## 5. Documentation (MkDocs)

```bash
cd docs
pip install -r requirements.txt
mkdocs serve
```

The docs are served at <http://localhost:8000>.

---

## Key flows

| Who | What | URL |
|-----|------|-----|
| Nurse / technician (field) | Scan QR → device info, manuals, report a fault | `/d/{id}` (no login) |
| Organization admin | Dashboard, devices, assign faults, manage members | `/dashboard`, `/devices`, `/faults`, `/groups` |
| Technician / engineer | Diagnose and repair assigned faults, log maintenance | `/tasks`, `/device/{id}` |
