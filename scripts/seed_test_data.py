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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

SCHEMA = os.getenv("DB_SCHEMA", "fixmymedtech")
DB_URI = os.environ.get(
    "DATABASE_URL",
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


def _bcrypt_hash(password: str) -> str:
    """BCrypt hash matching FastAPI-Users (pwdlib) format $2b$."""
    from pwdlib import PasswordHash
    from pwdlib.hashers.bcrypt import BcryptHasher
    return PasswordHash(hashers=[BcryptHasher()]).hash(password)


async def seed():
    engine = create_async_engine(DB_URI, echo=False)

    async with AsyncSession(engine) as db:
        # ── 1. Insert organizations ──────────────────────────
        for org in ORGANIZATIONS:
            await db.execute(
                text(f"""
                    INSERT INTO {SCHEMA}.organizations (id, name, country, region, type)
                    VALUES (:id, :name, :country, :region, :type)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name
                """),
                org,
            )
        await db.commit()
        print(f"✓ {len(ORGANIZATIONS)} organizations seeded")

        # ── 2. Create local users + profile + org membership ──
        for email, password, full_name, role, org_idx in USERS:
            org_id = ORGANIZATIONS[org_idx]["id"]
            user_id = uuid.uuid4()

            existing = await db.execute(
                text(f"SELECT id FROM {SCHEMA}.users WHERE email = :email"),
                {"email": email},
            )
            row = existing.mappings().first()
            if row:
                user_id = row["id"]
                print(f"  ~ {email:<30} already exists ({user_id})")
            else:
                await db.execute(
                    text(f"""
                        INSERT INTO {SCHEMA}.users
                            (id, email, hashed_password, is_active, is_superuser, is_verified, full_name)
                        VALUES (:id, :email, :pwd, TRUE, FALSE, TRUE, :full_name)
                    """),
                    {
                        "id": str(user_id),
                        "email": email,
                        "pwd": _bcrypt_hash(password),
                        "full_name": full_name,
                    },
                )
                print(f"  ✓ {email:<30} → {user_id}")

            # Insert into profiles. Test users are community members already
            # (status 'member' + Ambassador, see migration 029), so they can
            # use the whole platform without doing the welcome quests.
            await db.execute(
                text(f"""
                    INSERT INTO {SCHEMA}.profiles (id, username, full_name, country, member_status, member_since)
                    VALUES (:id, :username, :full_name, :country, 'member', NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        full_name=EXCLUDED.full_name
                """),
                {
                    "id": str(user_id),
                    "username": email.replace("@", "_").split(".")[0],
                    "full_name": full_name,
                    "country": ORGANIZATIONS[org_idx]["country"],
                },
            )
            await db.execute(
                text(f"""
                    INSERT INTO {SCHEMA}.member_roles (profile_id, role_key, country, source)
                    VALUES (:id, 'ambassador', :country, 'backfill')
                    ON CONFLICT DO NOTHING
                """),
                {"id": str(user_id), "country": ORGANIZATIONS[org_idx]["country"]},
            )

            # Insert into org_users (junction table)
            await db.execute(
                text(f"""
                    INSERT INTO {SCHEMA}.org_users (profile_id, organization_id, role)
                    VALUES (:profile_id, :org_id, :role)
                    ON CONFLICT (profile_id, organization_id) DO UPDATE SET role=EXCLUDED.role
                """),
                {"profile_id": str(user_id), "org_id": org_id, "role": role},
            )

        await db.commit()
        print(f"✓ {len(USERS)} users seeded")

        # ── 3. Community journey test accounts ───────────────
        # tech@mulago.org is Country lead for Uganda (sees Ugandan members and
        # applicants in /community/admin). applicant@test.org has just joined
        # and only sees /community/start.
        lead = (await db.execute(
            text(f"SELECT id FROM {SCHEMA}.users WHERE email = 'tech@mulago.org'"))).scalar()
        if lead:
            await db.execute(text(f"""
                INSERT INTO {SCHEMA}.member_roles (profile_id, role_key, country, source)
                VALUES (:id, 'country_lead', 'Uganda', 'assigned') ON CONFLICT DO NOTHING
            """), {"id": str(lead)})
        app_id = (await db.execute(
            text(f"SELECT id FROM {SCHEMA}.users WHERE email = 'applicant@test.org'"))).scalar()
        if not app_id:
            app_id = uuid.uuid4()
            await db.execute(text(f"""
                INSERT INTO {SCHEMA}.users (id, email, hashed_password, is_active, is_superuser, is_verified, full_name)
                VALUES (:id, 'applicant@test.org', :pwd, TRUE, FALSE, TRUE, 'Esi Boateng')
            """), {"id": str(app_id), "pwd": _bcrypt_hash("Pass123!")})
            await db.execute(text(f"""
                INSERT INTO {SCHEMA}.profiles (id, username, full_name, country, city)
                VALUES (:id, 'esi_boateng', 'Esi Boateng', 'Uganda', 'Kampala')
            """), {"id": str(app_id)})
            await db.execute(text(f"""
                INSERT INTO {SCHEMA}.org_users (profile_id, organization_id, role)
                VALUES (:id, :org, 'admin')
            """), {"id": str(app_id), "org": ORGANIZATIONS[0]["id"]})
            await db.execute(text(f"""
                INSERT INTO {SCHEMA}.community_applications (profile_id, kind, organisation, motivation)
                VALUES (:id, 'engineer', 'Mulago National Referral Hospital',
                        'Our incubators wait months for parts. I want to help fix that.')
            """), {"id": str(app_id)})
        await db.commit()
        print("✓ community accounts seeded: tech@mulago.org is Country lead (Uganda), "
              "applicant@test.org is an applicant")

    await engine.dispose()
    print("\nDone. You can now log in with any of these credentials.")
    print("Example: admin@mulago.org / Pass123!")


if __name__ == "__main__":
    asyncio.run(seed())
