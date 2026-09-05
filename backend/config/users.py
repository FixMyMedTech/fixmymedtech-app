"""FastAPI-Users integration.

Provides:
  - UserManager (password hashing via pwdlib/bcrypt, hooks for emails)
  - JWT auth backend (BearerTransport + JWTStrategy)
  - FastAPIUsers instance + current_active_user dependency
  - Dependency chain:  get_user_db → get_user_manager → ...
"""

import os
import uuid
import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from fastapi_users.password import BcryptHasher, PasswordHelper
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import User
from config.db_config import get_db

logger = logging.getLogger(__name__)

# ── Settings ──────────────────────────────────────────────────────────────────
JWT_SECRET    = os.getenv("AUTH_JWT_SECRET", "dev-local-jwt-secret-change-me")
FRONTEND_URL  = os.getenv("FRONTEND_URL", "http://localhost:8888")
API_BASE_URL  = os.getenv("API_BASE_URL", "http://localhost:8888")
TOKEN_TTL     = int(os.getenv("AUTH_TOKEN_TTL", str(60 * 24 * 7)))  # 7 days


# ── Password hashing ──────────────────────────────────────────────────────────
# FastAPI-Users 15 uses pwdlib.  We configure bcrypt so existing $2b$ hashes
# from the earlier manual auth still verify.  New hashes will also be bcrypt.
_password_helper = PasswordHelper(
    password_hash=PasswordHash(hashers=[BcryptHasher()])
)


# ── DB adapter ────────────────────────────────────────────────────────────────
async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)


# ── User manager ──────────────────────────────────────────────────────────────
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret  = JWT_SECRET
    verification_token_secret   = JWT_SECRET

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        logger.info("User registered: %s", user.email)
        try:
            from config.email import send_welcome_email, send_verification_email
            await send_welcome_email(user.email, user.full_name or user.email)
            token = await self._generate_verification_token(user)
            await send_verification_email(user.email, token, API_BASE_URL)
        except Exception:
            logger.exception("Failed to send registration emails for %s", user.email)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        logger.info("Password reset requested: %s", user.email)
        try:
            from config.email import send_reset_password_email
            await send_reset_password_email(user.email, token, FRONTEND_URL)
        except Exception:
            logger.exception("Failed to send password-reset email for %s", user.email)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        logger.info("Verification requested: %s", user.email)
        try:
            from config.email import send_verification_email
            await send_verification_email(user.email, token, API_BASE_URL)
        except Exception:
            logger.exception("Failed to send verification email for %s", user.email)

    async def on_after_update(
        self, user: User, update_dict: dict, request: Optional[Request] = None
    ) -> None:
        logger.info("User updated: %s — %s", user.email, list(update_dict.keys()))


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db, password_helper=_password_helper)


# ── JWT auth backend ──────────────────────────────────────────────────────────
bearer_transport = BearerTransport(tokenUrl="/api/auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=TOKEN_TTL)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# ── Public convenience objects ────────────────────────────────────────────────
fastapi_users = FastAPIUsers(get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
