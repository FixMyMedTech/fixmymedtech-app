# admin_auth.py — SQLAdmin authentication backend (superuser-only)

import os
import uuid
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy import text, create_engine
from dotenv import load_dotenv

load_dotenv()

# Sync engine for the auth check (runs in a thread-pool via SQLAdmin)
_uri = os.getenv("DATABASE_URL", "")
# Swap asyncpg → psycopg2 for the sync engine
_sync_uri = _uri.replace("postgresql+asyncpg://", "postgresql://")
_sync_engine = create_engine(_sync_uri, pool_size=2, echo=False)


class AdminAuth(AuthenticationBackend):
    """Only superusers may access the admin portal.

    Uses SQLAdmin's built-in SessionMiddleware so request.session is
    available.  On successful login the user_id is stored in the session;
    on each request authenticate() verifies the user exists and is_active +
    is_superuser.
    """

    def __init__(self):
        super().__init__(secret_key=os.getenv("AUTH_SESSION_SECRET", "dev-admin-session-secret"))

    # ── Login form submission ─────────────────────────────────────────────
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = (form.get("username") or "").strip().lower()
        password = form.get("password") or ""

        if not email or not password:
            return False

        with _sync_engine.begin() as conn:
            row = conn.execute(
                text("SELECT id, hashed_password, is_active, is_superuser "
                     "FROM fixmymedtech.users WHERE lower(email) = :e"),
                {"e": email},
            ).mappings().first()

        if not row or not row["is_active"] or not row["is_superuser"]:
            return False

        # Verify password via pwdlib (same hasher the UserManager uses)
        from pwdlib import PasswordHash
        from pwdlib.hashers.bcrypt import BcryptHasher
        hasher = PasswordHash(hashers=[BcryptHasher()])

        if not hasher.verify(password, row["hashed_password"]):
            return False

        request.session["admin_user_id"] = str(row["id"])
        return True

    # ── Logout ────────────────────────────────────────────────────────────
    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    # ── Per-request check ─────────────────────────────────────────────────
    async def authenticate(self, request: Request) -> bool:
        uid = request.session.get("admin_user_id")
        if not uid:
            return False

        try:
            user_uuid = uuid.UUID(uid)
        except (ValueError, TypeError):
            return False

        with _sync_engine.begin() as conn:
            row = conn.execute(
                text("SELECT is_active, is_superuser "
                     "FROM fixmymedtech.users WHERE id = :id"),
                {"id": user_uuid},
            ).mappings().first()

        return bool(row and row["is_active"] and row["is_superuser"])


async def require_superuser(request: Request):
    """FastAPI Depends() — raises 403 if the session user is not a superuser."""
    from fastapi import HTTPException
    uid = request.session.get("admin_user_id")
    if not uid:
        raise HTTPException(status_code=307, detail="Redirect to /admin/login")
    try:
        user_uuid = uuid.UUID(uid)
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="Invalid session")
    with _sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT is_active, is_superuser "
                 "FROM fixmymedtech.users WHERE id = :id"),
            {"id": user_uuid},
        ).mappings().first()
    if not row or not row["is_active"] or not row["is_superuser"]:
        raise HTTPException(status_code=403, detail="Not a superuser")
