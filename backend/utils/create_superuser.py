#!/usr/bin/env python3
"""
Create or promote a superuser for the FixMyMedTech admin portal.

Usage (inside Docker):
    docker compose exec backend python scripts/create_superuser.py

Usage (local, with DB reachable):
    python scripts/create_superuser.py
"""

import sys
import os

# Ensure backend/ is on the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from admin_auth import _sync_engine
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher


def get_input(prompt: str, hidden: bool = False) -> str:
    if hidden:
        import getpass
        return getpass.getpass(prompt).strip()
    return input(prompt).strip()


def main():
    print("\n=== FixMyMedTech — Create Superuser ===\n")

    email = get_input("Email: ").lower()
    if not email or "@" not in email:
        print("Invalid email.")
        sys.exit(1)

    full_name = get_input("Full name: ")
    password = get_input("Password: ", hidden=True)
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    hasher = PasswordHash(hashers=[BcryptHasher()])
    hashed = hasher.hash(password)

    with _sync_engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id, is_superuser FROM fixmymedtech.users WHERE email = :e"),
            {"e": email},
        ).mappings().first()

        if existing:
            if existing["is_superuser"]:
                print(f"\n'{email}' is already a superuser.")
                sys.exit(0)
            conn.execute(
                text(
                    "UPDATE fixmymedtech.users "
                    "SET is_superuser = true, hashed_password = :pw, "
                    "    is_active = true, is_verified = true, "
                    "    full_name = COALESCE(:name, full_name) "
                    "WHERE email = :e"
                ),
                {"e": email, "pw": hashed, "name": full_name or None},
            )
            print(f"\n'{email}' has been promoted to superuser.")
        else:
            import uuid
            uid = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO fixmymedtech.users "
                    "(id, email, full_name, hashed_password, is_active, is_superuser, is_verified) "
                    "VALUES (:id, :email, :name, :pw, true, true, true)"
                ),
                {"id": uid, "email": email, "name": full_name, "pw": hashed},
            )

            # Create a profile + default org so the user is functional
            username = email.split("@")[0].replace(".", "_")
            conn.execute(
                text(
                    "INSERT INTO fixmymedtech.profiles (id, username, full_name) "
                    "VALUES (:id, :username, :name)"
                ),
                {"id": uid, "username": username, "name": full_name},
            )
            org_id = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO fixmymedtech.organizations (id, name, country, type) "
                    "VALUES (:id, :name, '', 'hospital')"
                ),
                {"id": org_id, "name": full_name},
            )
            conn.execute(
                text(
                    "INSERT INTO fixmymedtech.org_users (id, profile_id, organization_id, role) "
                    "VALUES (:id, :pid, :oid, 'admin')"
                ),
                {"id": uuid.uuid4(), "pid": uid, "oid": org_id},
            )
            print(f"\nSuperuser '{email}' created.")
            print(f"  Login at: http://localhost:8888/admin/")

    print()


if __name__ == "__main__":
    main()
