# FixMyMedTech — Setup Guide

---

## 1. Supabase setup

1. Create a project at https://supabase.com
2. Go to **SQL Editor** → paste and run `supabase/schema.sql`
3. Go to **Project Settings → API** → copy:
   - Project URL
   - `anon` public key
   - `service_role` secret key

---

## 2. Backend setup

```bash
cd backend
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY

pip install -r requirements.txt
uvicorn main:app --reload
# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## 3. Frontend setup

```bash
cd frontend
cp .env.example .env
# Set PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
# Runs at http://localhost:5173
```

---

## 4. Production deploy (your server)

### Backend (with systemd or supervisor)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Key flows

| Who                        | What                                             | URL                         |
| -------------------------- | ------------------------------------------------ | --------------------------- |
| Nurse / technician (field) | Scan QR → see device info, manuals, report fault | `/d/{id}` — no login needed |
| Hospital admin             | Dashboard, manage devices, see faults            | `/dashboard`, `/devices`    |
| Biomedical engineer        | Update device status, log maintenance            | `/devices/{id}`             |

---

## Offline behaviour (PWA) - Nice to have

- Device pages (`/d/{id}`) are cached by the Service Worker after first visit
- Manuals/PDFs cached for 30 days
- API responses cached for 7 days
- Fault reports require internet connection to submit
