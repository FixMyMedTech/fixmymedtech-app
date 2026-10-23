# routers/feedback.py
#
# Feedback and issue reports from the floating "?" button on every page.
#
# Anyone can send one, logged in or not (public QR pages have no login). A
# report is always stored first, then posted to a Discord forum channel as its
# own thread in the background, so the sender never waits on Discord and
# nothing is lost if Discord is down. discord_status records the outcome.
#
# Only the summary, description, page, language, screenshot and the sender's
# username reach Discord. Email addresses never do.

import asyncio
import logging
import os
import time
import uuid
from urllib.parse import quote
from collections import defaultdict, deque
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File as FileParam, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import AsyncSessionLocal, get_db
from config.discord import create_forum_thread, discord_enabled
from config.storage import get_file, upload_file
from models.models import Feedback, Profile
from utils.profile import get_optional_profile

router = APIRouter()
logger = logging.getLogger("feedback")

TYPES = ("feedback", "issue")
LANGS = ("en", "es", "fr")
SUMMARY_MAX = 100        # also Discord's thread-name limit
DESCRIPTION_MAX = 4000
PAGE_MAX = 500
EMAIL_MAX = 254
SCREENSHOT_MAX = 2 * 1024 * 1024
SCREENSHOT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# Public base URL of this deployment (local, dev or prod). Discord shows the
# full page URL so the team can tell which environment a report came from.
# Taken from server config, never from the form, so it can't be faked.
BASE_URL = os.getenv("FRONTEND_URL", "").rstrip("/")


# ── rate limiting ────────────────────────────────────────────────────────────
#
# In-memory, per backend process (the app runs a single uvicorn worker).
# Logged-in senders are limited per profile. Anonymous reports all arrive from
# the frontend container, so the caller's IP says nothing about the visitor;
# they share one global budget instead, which still caps how fast anyone can
# flood the Discord channel.

RATE_WINDOW = 3600
RATE_PER_USER = 10
RATE_ANONYMOUS = 30
_hits: dict[str, deque] = defaultdict(deque)


def _allow(key: str, limit: int) -> bool:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


# ── submit ───────────────────────────────────────────────────────────────────

@router.post("/")
async def submit_feedback(
    type: str = Form(...),
    summary: str = Form(...),
    description: str = Form(...),
    page: Optional[str] = Form(None),
    lang: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    screenshot: Optional[UploadFile] = FileParam(None),
    profile: Optional[Profile] = Depends(get_optional_profile),
    db: AsyncSession = Depends(get_db),
):
    summary = " ".join(summary.split())
    description = description.strip()
    if type not in TYPES:
        raise HTTPException(status_code=400, detail="Unknown feedback type")
    if not summary or len(summary) > SUMMARY_MAX:
        raise HTTPException(status_code=400, detail=f"Summary must be 1–{SUMMARY_MAX} characters")
    if not description or len(description) > DESCRIPTION_MAX:
        raise HTTPException(status_code=400, detail=f"Description must be 1–{DESCRIPTION_MAX} characters")

    # Only an in-app path is kept: this ends up as a link-like value in
    # Discord, so an arbitrary URL from the form is dropped.
    page = (page or "").strip()
    if not page.startswith("/") or page.startswith("//") or len(page) > PAGE_MAX:
        page = None
    lang = lang if lang in LANGS else None

    contact_email = (contact_email or "").strip() or None
    if profile is not None:
        contact_email = None  # the profile already identifies them
    elif contact_email and (len(contact_email) > EMAIL_MAX or "@" not in contact_email):
        raise HTTPException(status_code=400, detail="Invalid contact email")

    shot: Optional[tuple[bytes, str]] = None
    if screenshot is not None and screenshot.filename:
        ctype = (screenshot.content_type or "").lower()
        if ctype not in SCREENSHOT_TYPES:
            raise HTTPException(status_code=400, detail="Screenshot must be a JPEG, PNG or WebP image")
        content = await screenshot.read(SCREENSHOT_MAX + 1)
        if len(content) > SCREENSHOT_MAX:
            raise HTTPException(status_code=413, detail="Screenshot is too large")
        if content:
            shot = (content, ctype)

    key = f"profile:{profile.id}" if profile else "anonymous"
    if not _allow(key, RATE_PER_USER if profile else RATE_ANONYMOUS):
        raise HTTPException(status_code=429, detail="Too many reports, please try again later")

    fb = Feedback(
        id=uuid.uuid4(),
        type=type,
        summary=summary,
        description=description,
        page=page,
        lang=lang,
        profile_id=profile.id if profile else None,
        contact_email=contact_email,
        discord_status="pending" if discord_enabled() else "disabled",
    )
    if shot:
        content, ctype = shot
        fb.screenshot_key = await upload_file(
            "feedback", str(fb.id), f"screenshot{SCREENSHOT_TYPES[ctype]}", content, ctype,
        )
    db.add(fb)
    await db.commit()

    if discord_enabled():
        _spawn(_post_to_discord(fb.id))

    return {"id": fb.id}


# ── Discord (background) ─────────────────────────────────────────────────────

_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    # Keep a reference until done; the event loop only holds weak ones.
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _discord_content(fb: Feedback, username: Optional[str]) -> str:
    kind = "🐞 Issue" if fb.type == "issue" else "💬 Feedback"
    who = f"**{username}**" if username else "an anonymous visitor"
    meta = [f"{kind} from {who}"]
    if fb.page:
        # Percent-encode anything that could break out of the <...> link.
        url = BASE_URL + quote(fb.page, safe="/?=&%#:@+,;~-._!$'()*")
        meta.append(f"Page: <{url}>")  # <...> keeps it a link without an embed preview
    if fb.lang:
        meta.append(f"Language: {fb.lang}")
    meta.append(f"Ref: `{fb.id}`")
    return fb.description + "\n\n" + "\n".join(f"-# {line}" for line in meta)


async def _post_to_discord(feedback_id: uuid.UUID) -> None:
    """Best-effort and never raising: the outcome lands in discord_status."""
    async with AsyncSessionLocal() as db:
        fb = (await db.execute(select(Feedback).where(Feedback.id == feedback_id))).scalar_one_or_none()
        if fb is None:
            return
        try:
            username = None
            if fb.profile_id:
                username = (await db.execute(
                    select(Profile.username).where(Profile.id == fb.profile_id)
                )).scalar_one_or_none()

            attachment = None
            if fb.screenshot_key:
                obj = await get_file(fb.screenshot_key)
                if obj is not None:
                    data, ctype = obj
                    attachment = (os.path.basename(fb.screenshot_key), data, ctype)

            fb.discord_thread_id = await create_forum_thread(
                fb.summary, _discord_content(fb, username), fb.type, attachment,
            )
            fb.discord_status = "sent"
        except httpx.HTTPStatusError as e:
            # Not str(e): it contains the webhook URL, and the URL is the secret.
            logger.warning("posting feedback %s to Discord failed: HTTP %s %s",
                           feedback_id, e.response.status_code, e.response.text[:300])
            fb.discord_status = "failed"
        except Exception as e:  # noqa: BLE001
            logger.warning("posting feedback %s to Discord failed: %s",
                           feedback_id, type(e).__name__)
            fb.discord_status = "failed"
        await db.commit()
