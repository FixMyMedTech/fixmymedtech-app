#!/usr/bin/env python3
"""
Create or promote a superuser for the FixMyMedTech admin portal.

Usage (interactive, inside Docker):
    docker compose exec backend python utils/create_superuser.py

Usage (local, with DB reachable):
    python utils/create_superuser.py

Automated (no prompts) — set these env vars and the backend will ensure a
superuser on every startup, right after migrations:
    SUPERUSER_EMAIL=als@example.org
    SUPERUSER_PASSWORD=change-me-8-chars-min
    SUPERUSER_NAME="Ops Admin"            # optional
"""

import asyncio
import os
import sys
import uuid

import sqlalchemy as sa
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.db_config import engine

hasher = PasswordHash(hashers=[BcryptHasher()])


async def ensure_superuser(email: str, password: str, full_name: str) -> str:
    """Create the user or promote an existing one. Returns a status message."""

    email = (email or "").lower().strip()
    password = password or ""
    full_name = (full_name or "").strip()

    if not email or "@" not in email:
        return "invalid: email missing or malformed"
    if len(password) < 8:
        return "invalid: password must be at least 8 characters"

    hashed = hasher.hash(password)

    async with engine.begin() as conn:
        existing = (
            await conn.execute(
                sa.text(
                    "SELECT id, is_superuser FROM fixmymedtech.users "
                    "WHERE email = :e"
                ),
                {"e": email},
            )
        ).mappings().first()

        if existing:
            if existing["is_superuser"]:
                return f"{email} is already a superuser (nothing to do)"
            await conn.execute(
                sa.text(
                    "UPDATE fixmymedtech.users "
                    "SET is_superuser = true, hashed_password = :pw, "
                    "    is_active = true, is_verified = true, "
                    "    full_name = COALESCE(:name, full_name) "
                    "WHERE email = :e"
                ),
                {"e": email, "pw": hashed, "name": full_name or None},
            )
            return f"{email} promoted to superuser"
        uid = uuid.uuid4()
        await conn.execute(
            sa.text(
                "INSERT INTO fixmymedtech.users "
                "(id, email, full_name, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, :name, :pw, true, true, true)"
            ),
            {"id": uid, "email": email, "name": full_name, "pw": hashed},
        )

        username = email.split("@")[0].replace(".", "_")
        await conn.execute(
            sa.text(
                "INSERT INTO fixmymedtech.profiles (id, username, full_name) "
                "VALUES (:id, :username, :name)"
            ),
            {"id": uid, "username": username, "name": full_name},
        )
        org_id = uuid.uuid4()
        await conn.execute(
            sa.text(
                "INSERT INTO fixmymedtech.organizations (id, name, country, type) "
                "VALUES (:id, :name, '', 'hospital')"
            ),
            {"id": org_id, "name": full_name or email},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO fixmymedtech.org_users (id, profile_id, organization_id, role) "
                "VALUES (:id, :pid, :oid, 'admin')"
            ),
            {"id": uuid.uuid4(), "pid": uid, "oid": org_id},
        )
        return f"superuser '{email}' created (profile + default org attached)"

    # unreachable
    return ""


async def bootstrap_superuser_from_env() -> bool:
    """Create/promote a superuser from SUPERUSER_EMAIL / SUPERUSER_PASSWORD.

    Called automatically during backend startup. No-op unless both env vars
    are set. Returns True when configured (even if creation failed).
    """

    email = os.getenv("SUPERUSER_EMAIL", "").strip()
    password = os.getenv("SUPERUSER_PASSWORD", "").strip()
    full_name = os.getenv("SUPERUSER_NAME", "").strip()

    if not email or not password:
        return False

    print("[bootstrap] SUPERUSER_EMAIL set — ensuring superuser exists...", flush=True)
    message = await ensure_superuser(email, password, full_name)
    print(f"[bootstrap] {message}", flush=True)
    return True


def _interactive_input(prompt: str, hidden: bool = False) -> str:
    if hidden:
        import getpass

        return getpass.getpass(prompt).strip()
    return input(prompt).strip()


async def _interactive():
    print("\n=== FixMyMedTech — Create Superuser ===\n")
    email = _interactive_input("Email: ").lower()
    full_name = _interactive_input("Full name: ")
    password = _interactive_input("Password: ", hidden=True)

    message = await ensure_superuser(email, password, full_name)
    if message.startswith("invalid"):
        print(message)
        sys.exit(1)
    print(f"\n{message}")
    print("  Admin portal: http://localhost:8888/admin/\n")


if __name__ == "__main__":
    if os.getenv("SUPERUSER_EMAIL") and os.getenv("SUPERUSER_PASSWORD"):
        asyncio.run(bootstrap_superuser_from_env())
    else:
        asyncio.run(_interactive())