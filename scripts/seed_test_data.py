#!/usr/bin/env python3
"""Seed test organizations and users for local development.

Usage:
    docker compose exec backend python /app/scripts/seed_test_data.py
    # or from host:
    python scripts/seed_test_data.py
"""

import os, sys, uuid
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_API_SECRET_KEY"]
DB_URI = os.environ.get(
    "SUPABASE_DB_URI",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/fixmymedtech",
)

# ── Org definitions ──────────────────────────────────────────
ORGANIZATIONS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Mulago National Referral Hospital",
        "country": "Uganda",
        "region": "Kampala",
        "type": "hospital",
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "Douala General Hospital",
        "country": "Cameroon",
        "region": "Douala",
        "type": "hospital",
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "name": "Muhimbili Medical Centre",
        "country": "Tanzania",
        "region": "Dar es Salaam",
        "type": "hospital",
    },
    {
        "id": "00000000-0000-0000-0000-000000000004",
        "name": "Kigali Health Institute Clinic",
        "country": "Rwanda",
        "region": "Kigali",
        "type": "clinic",
    },
    {
        "id": "00000000-0000-0000-0000-000000000005",
        "name": "Lilongwe Engineering Workshop",
        "country": "Malawi",
        "region": "Lilongwe",
        "type": "engineering",
    },
]

# ── User definitions ─────────────────────────────────────────
USERS = [
    # (email, password, full_name, role, org_index)
    ("admin@mulago.org",       "Pass123!", "Dr. Sarah Nakato",     "admin",             0),
    ("tech@mulago.org",        "Pass123!", "John Okello",          "technician",        0),
    ("nurse@mulago.org",       "Pass123!", "Grace Akello",         "clinical_staff",    0),
    ("eng@mulago.org",         "Pass123!", "Paul Wasswa",          "engineering_staff", 0),

    ("admin@kenyatta.org",     "Pass123!", "Dr. James Kamau",      "admin",             1),
    ("tech@kenyatta.org",      "Pass123!", "Mary Wanjiku",         "technician",        1),

    ("admin@muhimbili.org",    "Pass123!", "Dr. Aisha Mohamed",    "admin",             2),
    ("tech@muhimbili.org",     "Pass123!", "Hamza Juma",           "technician",        2),

    ("admin@kigali.org",       "Pass123!", "Dr. Eric Mugisha",     "admin",             3),
    ("tech@kigali.org",        "Pass123!", "Diane Uwimana",        "technician",        3),

    ("admin@lilongwe.org",     "Pass123!", "Chifundo Banda",       "admin",             4),
    ("tech@lilongwe.org",      "Pass123!", "Tionge Phiri",         "technician",        4),
]


async def seed():
    engine = create_async_engine(DB_URI, echo=False)
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    async with AsyncSession(engine) as db:
        # ── 1. Insert organizations ──────────────────────────
        for org in ORGANIZATIONS:
            await db.execute(
                text("""
                    INSERT INTO fixmymedtech.organizations (id, name, country, region, type)
                    VALUES (:id, :name, :country, :region, :type)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name
                """),
                org,
            )
        await db.commit()
        print(f"✓ {len(ORGANIZATIONS)} organizations seeded")

        # ── 2. Create users via Supabase Auth + profile ──────
        for email, password, full_name, role, org_idx in USERS:
            org_id = ORGANIZATIONS[org_idx]["id"]

            try:
                res = sb.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                })
                user_id = res.user.id
                print(f"  ✓ {email:<30} → {user_id}")
            except Exception as e:
                if "already exists" in str(e):
                    # Try to find existing user
                    try:
                        users = sb.auth.admin.list_users()
                        match = [u for u in users if u.email == email]
                        if match:
                            user_id = match[0].id
                            print(f"  ~ {email:<30} already exists ({user_id})")
                        else:
                            print(f"  ✗ {email:<30} {e}")
                            continue
                    except Exception as e2:
                        print(f"  ✗ {email:<30} {e2}")
                        continue
                else:
                    print(f"  ✗ {email:<30} {e}")
                    continue

            # Insert into auth.users for FK compatibility
            await db.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_id, "email": email},
            )

            # Insert into profiles
            await db.execute(
                text("""
                    INSERT INTO fixmymedtech.profiles (id, organization_id, full_name, role)
                    VALUES (:id, :org_id, :full_name, :role)
                    ON CONFLICT (id) DO UPDATE SET
                        organization_id=EXCLUDED.organization_id,
                        full_name=EXCLUDED.full_name,
                        role=EXCLUDED.role
                """),
                {"id": user_id, "org_id": org_id, "full_name": full_name, "role": role},
            )

        await db.commit()
        print(f"✓ {len(USERS)} users seeded")

    await engine.dispose()
    print("\nDone. You can now log in with any of these credentials.")
    print("Example: admin@mulago.org / Pass123!")


if __name__ == "__main__":
    asyncio.run(seed())
