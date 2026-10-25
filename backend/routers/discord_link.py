# routers/discord_link.py — link an app account to a Discord account, and
# re-send the email verification link, both from the profile page.
#
# Mounted under /api/auth.
#
# Linking reuses the Discord app already registered for "Continue with
# Discord", including its redirect URL, so nothing new has to be configured in
# the Discord developer portal:
#
#   1. POST /me/discord/link-start (logged in, called server-side by the
#      frontend) returns a URL carrying a short-lived, single-use ticket.
#   2. The browser opens GET /discord/link?ticket=…, which remembers the user
#      in the backend session and redirects to Discord.
#   3. Discord redirects to the normal /oauth/discord/callback. routers/oauth.py
#      sees the pending link in the session and calls finish_discord_link()
#      instead of logging someone in.
#
# The ticket is needed because the browser never holds the user's JWT (it
# lives in the frontend's session), so step 2 can't be authenticated directly.
#
# The first link of an account posts a welcome message in the Discord welcome
# channel (DISCORD_WELCOME_WEBHOOK_URL), mentioning the user. Never twice.

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi_users.jwt import decode_jwt, generate_jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import AsyncSessionLocal, get_db
from config.discord import post_welcome, welcome_enabled
from config.users import JWT_SECRET, UserManager, current_active_user, get_user_manager
from models.models import Profile, User
from utils.background import spawn

router = APIRouter()
logger = logging.getLogger("discord_link")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5001").rstrip("/")

TICKET_AUDIENCE = "fixmymedtech:discord-link"
TICKET_LIFETIME = 600            # seconds to complete the Discord consent screen
SESSION_KEY = "discord_link"     # backend session entry for a pending link
_used_tickets: dict[str, float] = {}   # jti → expiry, so a ticket works once


def discord_login_available() -> bool:
    from config.oauth import oauth
    return getattr(oauth, "discord", None) is not None


# ── linking ──────────────────────────────────────────────────────────────────

async def link_discord_account(db: AsyncSession, user_id, discord_id: str,
                               discord_username: str, replace: bool = True) -> str:
    """Link ``discord_id`` to the user. Returns 'linked', 'unchanged' or 'taken'
    (that Discord account belongs to another app account). Commits.

    ``replace=False`` (used on Discord login) keeps a different Discord
    account the user linked earlier instead of switching to this one."""
    other = (await db.execute(
        select(User.id).where(User.discord_user_id == discord_id, User.id != user_id)
    )).scalar_one_or_none()
    if other is not None:
        return "taken"

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    if user.discord_user_id == discord_id:
        user.discord_username = discord_username  # they may have renamed
        await db.commit()
        return "unchanged"
    if user.discord_user_id and not replace:
        return "unchanged"

    user.discord_user_id = discord_id
    user.discord_username = discord_username
    user.discord_linked_at = datetime.now(timezone.utc)
    welcome = welcome_enabled() and user.discord_welcomed_at is None
    if welcome:
        # Claimed now so two quick links can't both post; released on failure.
        user.discord_welcomed_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError:
        # Linked to someone else between our check and the commit.
        await db.rollback()
        return "taken"

    if welcome:
        spawn(_send_welcome(user.id, discord_id))
    return "linked"


def discord_identity(info: dict) -> tuple[str, str]:
    """(user id, display name) from Discord's /users/@me response."""
    return str(info["id"]), info.get("global_name") or info.get("username") or ""


async def finish_discord_link(request: Request, client, db: AsyncSession,
                              user_id: str) -> RedirectResponse:
    """Second half of the link flow, called from the Discord OAuth callback."""
    try:
        token = await client.authorize_access_token(request)
        info = dict(await client.userinfo(token=token))
        discord_id, discord_username = discord_identity(info)
    except Exception as e:  # noqa: BLE001 — includes the user pressing Cancel
        logger.info("Discord link for %s not completed: %s", user_id, type(e).__name__)
        return _back_to_profile("error")

    status = await link_discord_account(db, uuid.UUID(user_id), discord_id, discord_username)
    return _back_to_profile("taken" if status == "taken" else "linked")


def pop_pending_link(request: Request) -> Optional[str]:
    """The user id of a link started in this browser in the last few minutes."""
    pending = request.session.pop(SESSION_KEY, None)
    if not pending or time.time() - pending.get("at", 0) > TICKET_LIFETIME:
        return None
    return pending.get("user")


def _back_to_profile(result: str) -> RedirectResponse:
    return RedirectResponse(f"{FRONTEND_URL}/profile?discord={result}", status_code=302)


# ── welcome message (background) ─────────────────────────────────────────────

def _md(text: str) -> str:
    """Escape Discord markdown in user-typed text."""
    for ch in "\\*_~`|>#[]()":
        text = text.replace(ch, "\\" + ch)
    return text.strip()


async def _send_welcome(user_id, discord_id: str) -> None:
    """Best-effort and never raising. On failure the claim on
    discord_welcomed_at is released so a later link can try again."""
    async with AsyncSessionLocal() as db:
        profile = (await db.execute(
            select(Profile).where(Profile.id == user_id)
        )).scalar_one_or_none()

        # Name and country from the profile only.
        details = []
        if profile is not None:
            if profile.full_name:
                details.append(_md(profile.full_name))
            if profile.country:
                details.append(_md(profile.country))

        content = f"👋 Welcome <@{discord_id}> to **FixMyMedTech**!"
        if details:
            content += "\n-# " + " · ".join(d for d in details if d)
        try:
            await post_welcome(content, discord_id)
            return
        except httpx.HTTPStatusError as e:
            # Not str(e): it contains the webhook URL, and the URL is the secret.
            logger.warning("Discord welcome for %s failed: HTTP %s %s",
                           user_id, e.response.status_code, e.response.text[:300])
        except Exception as e:  # noqa: BLE001
            logger.warning("Discord welcome for %s failed: %s", user_id, type(e).__name__)

        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is not None:
            user.discord_welcomed_at = None
            await db.commit()


# ── endpoints ────────────────────────────────────────────────────────────────

@router.post("/me/discord/link-start")
async def discord_link_start(user: User = Depends(current_active_user)):
    if not discord_login_available():
        raise HTTPException(status_code=503, detail="Discord is not configured")
    ticket = generate_jwt(
        {"sub": str(user.id), "aud": TICKET_AUDIENCE, "jti": uuid.uuid4().hex},
        JWT_SECRET, TICKET_LIFETIME,
    )
    return {"url": f"{FRONTEND_URL}/api/auth/discord/link?ticket={ticket}"}


@router.get("/discord/link")
async def discord_link_redirect(ticket: str, request: Request):
    try:
        data = decode_jwt(ticket, JWT_SECRET, [TICKET_AUDIENCE])
    except Exception:
        return _back_to_profile("expired")

    now = time.time()
    for jti, exp in list(_used_tickets.items()):
        if exp < now:
            del _used_tickets[jti]
    if data["jti"] in _used_tickets:
        return _back_to_profile("expired")
    _used_tickets[data["jti"]] = now + TICKET_LIFETIME

    from config.oauth import oauth
    request.session[SESSION_KEY] = {"user": data["sub"], "at": now}
    redirect_uri = request.url_for("oauth_callback", provider="discord")
    # Linking only needs the Discord identity, not the email.
    return await oauth.discord.authorize_redirect(request, redirect_uri, scope="identify")


@router.delete("/me/discord")
async def discord_unlink(user: User = Depends(current_active_user),
                         db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    row.discord_user_id = None
    row.discord_username = None
    row.discord_linked_at = None
    # discord_welcomed_at is kept on purpose: no second welcome on reconnect.
    await db.commit()
    return {"status": "unlinked"}


# ── email verification (resend, logged in) ───────────────────────────────────

VERIFY_COOLDOWN = 60   # seconds between verification emails per account
_last_verify: dict[str, float] = {}


@router.post("/me/request-verification")
async def request_my_verification(
    request: Request,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    if user.is_verified:
        return {"status": "already_verified"}
    now = time.monotonic()
    if now - _last_verify.get(str(user.id), -VERIFY_COOLDOWN) < VERIFY_COOLDOWN:
        raise HTTPException(status_code=429, detail="Please wait a minute before asking again")
    _last_verify[str(user.id)] = now
    await user_manager.request_verify(user, request=request)
    return {"status": "sent"}
