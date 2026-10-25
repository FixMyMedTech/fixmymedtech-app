# routers/profile.py — Profile endpoints (me, avatar, stats, network directory)
#
# Mounted under /api/auth, keeping the same frontend contract:
#   GET   /api/auth/me         → {id, username, full_name, country, avatar_key, email,
#                                  is_verified, discord, organizations}
#   PATCH /api/auth/me         → {id, username, full_name, country, avatar_key}
#   POST  /api/auth/me/photo   → {avatar_key, mime_type}
#   GET   /api/auth/me/photo   → avatar image bytes
#   GET   /api/auth/me/stats   → {devices_registered, faults_resolved, maintenance_performed}
#   GET   /api/auth/profiles   → {items, total, limit, offset, sort, dir}  (network directory)
#   GET   /api/auth/profiles/{id}        → a single profile, for any signed-in member
#   GET   /api/auth/profiles/{id}/photo  → that profile's avatar

import asyncio
import io
import os
import uuid

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File as FileParam
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from models.models import Profile, OrgUser, User, Device, FaultReport, MaintenanceLog
from config.db_config import get_db
from config.storage import upload_file, get_file, delete_file
from config.users import current_active_user
from utils.profile import get_current_profile

router = APIRouter()


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    country: Optional[str] = None


# ── Me ─────────────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships).selectinload(OrgUser.organization))
        .where(Profile.id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    from routers.discord_link import discord_login_available
    return {
        "id": profile.id,
        "username": profile.username,
        "full_name": profile.full_name,
        "country": profile.country,
        "avatar_key": profile.avatar_key,
        "email": user.email,
        "is_verified": user.is_verified,
        "discord": {
            "available": discord_login_available(),
            "linked": bool(user.discord_user_id),
            "username": user.discord_username,
        },
        "organizations": [
            {
                "id": m.organization_id,
                "name": m.organization.name if m.organization else None,
                "country": m.organization.country if m.organization else None,
                "role": m.role,
            }
            for m in profile.org_memberships
        ],
    }


@router.patch("/me")
async def update_me(
    body: ProfileUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.full_name is not None:
        profile.full_name = body.full_name
    if body.username is not None:
        candidate = body.username.strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        existing = await db.execute(
            text("SELECT 1 FROM fixmymedtech.profiles WHERE username = :u AND id != :id"),
            {"u": candidate, "id": str(profile.id)},
        )
        if existing.scalar():
            raise HTTPException(status_code=400, detail="Username already taken")
        profile.username = candidate
    if body.country is not None:
        profile.country = body.country.strip() or None
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": profile.id,
        "username": profile.username,
        "full_name": profile.full_name,
        "country": profile.country,
        "avatar_key": profile.avatar_key,
    }


# ── Profile picture (avatar) ────────────────────────────────────────────────

AVATAR_MAX_BYTES = 8 * 1024 * 1024
AVATAR_MAX_DIM = 512
AVATAR_JPEG_QUALITY = 90


def _make_avatar_bytes(content: bytes) -> tuple[bytes, str, str] | None:
    """Downscale + re-encode an avatar to a small JPEG. None on failure.

    Corrects EXIF orientation and composites transparency onto white, then
    returns ``(bytes, "image/jpeg", "avatar.jpg")``.
    """
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(content))
        img.load()
        img = ImageOps.exif_transpose(img)

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            white = Image.new("RGB", img.size, (255, 255, 255))
            white.paste(img, mask=img.split()[3])
            img = white
        else:
            img = img.convert("RGB")

        img.thumbnail((AVATAR_MAX_DIM, AVATAR_MAX_DIM), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=AVATAR_JPEG_QUALITY, optimize=True, progressive=True)
        return buf.getvalue(), "image/jpeg", "avatar.jpg"
    except Exception:  # noqa: BLE001
        return None


@router.post("/me/photo")
async def upload_avatar(
    photo: UploadFile = FileParam(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    content = await photo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(content) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 8MB)")

    out = await asyncio.to_thread(_make_avatar_bytes, content)
    if out:
        content, ctype, filename = out
    else:
        ctype = photo.content_type or "application/octet-stream"
        filename = photo.filename or "avatar.jpg"

    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    key = await upload_file(
        "profiles", str(profile.id), filename, content, ctype,
        object_id=f"avatar_{uuid.uuid4().hex}{ext}",
    )
    old_key = profile.avatar_key
    profile.avatar_key = key
    await db.commit()
    if old_key and old_key != key:
        delete_file(old_key)
    return {"avatar_key": key, "mime_type": ctype}


@router.get("/me/photo")
async def get_avatar(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()
    if not profile or not profile.avatar_key:
        raise HTTPException(status_code=404, detail="No avatar")
    obj = await get_file(profile.avatar_key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Avatar not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)


# ── Stats ──────────────────────────────────────────────────────────────────────

async def _counts_for(db: AsyncSession, profile_id) -> dict:
    """The four activity measures for one profile.

    Shared by /me/stats and /profiles/{id} so a member's own page and their
    public page can never disagree, and so both match what the Network table
    sorts by.
    """
    subs, metrics = _metric_subqueries()
    row = (
        await db.execute(
            select(*metrics)
            .select_from(Profile)
            .outerjoin(subs[0], subs[0].c.pid == Profile.id)
            .outerjoin(subs[1], subs[1].c.pid == Profile.id)
            .outerjoin(subs[2], subs[2].c.pid == Profile.id)
            .outerjoin(subs[3], subs[3].c.pid == Profile.id)
            .where(Profile.id == profile_id)
        )
    ).one()
    devices_n, repairs_n, maintenance_n, invites_n = (int(v or 0) for v in row)
    return {
        "devices_registered": devices_n,
        "faults_resolved": repairs_n,
        "maintenance_performed": maintenance_n,
        "invites": invites_n,
    }


@router.get("/me/stats")
async def get_profile_stats(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return await _counts_for(db, profile.id)


# ── Other profiles (read-only) ──────────────────────────────────────────────────
#
# Any signed-in member may open any other member's profile — that is what the
# Network directory is for, and the "Registered by" link on a device already
# points here. Only the public fields are returned: never the linked User
# (which carries the hashed password and email).

async def _load_viewable_profile(db: AsyncSession, viewer_id, profile_id) -> Profile:
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships).selectinload(OrgUser.organization))
        .where(Profile.id == profile_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Profile not found")
    return target


def _card(p: Profile, stats: dict | None = None) -> dict:
    """Network-directory card. Hand-built: never touch p.user, which lazy-loads
    the auth User and would put hashed_password in the response."""
    primary = p.org_memberships[0] if p.org_memberships else None
    return {
        "id": p.id,
        "username": p.username,
        "full_name": p.full_name,
        "country": p.country,
        "avatar_key": p.avatar_key,
        "role": primary.role if primary else None,
        "organization": (
            {
                "id": primary.organization_id,
                "name": primary.organization.name if primary.organization else None,
            }
            if primary else None
        ),
        # Activity counts, for the table view. The cards ignore them.
        **(stats or {}),
    }


# ── Directory ordering ────────────────────────────────────────────────────────
#
# Four activity measures, aggregated in SQL rather than per row: the sort has
# to run across every matching member BEFORE pagination, so counting them one
# profile at a time would both paginate wrongly and hammer the database.

# Repairs credit the person who RESOLVED the fault (not whoever it was assigned
# to), and maintenance counts only logs that were actually closed.
SORTABLE = ("devices", "repairs", "maintenance", "invites", "name")

# `name` is not a metric, so it is defined separately below.
DEFAULT_SORT = "default"
DEFAULT_DIR = "desc"


def _metric_subqueries():
    """Returns (subqueries, metrics). Each measure is grouped once in SQL and
    joined as a derived table, so sorting never costs a query per member."""
    dev = (
        select(Device.registered_by.label("pid"), func.count().label("n"))
        .group_by(Device.registered_by)
        .subquery()
    )
    rep = (
        select(FaultReport.resolved_by.label("pid"), func.count().label("n"))
        .where(FaultReport.status == "resolved")
        .group_by(FaultReport.resolved_by)
        .subquery()
    )
    mnt = (
        select(MaintenanceLog.performed_by.label("pid"), func.count().label("n"))
        .where(MaintenanceLog.status == "closed")
        .group_by(MaintenanceLog.performed_by)
        .subquery()
    )
    inv = (
        select(User.invited_by.label("pid"), func.count().label("n"))
        .where(User.invited_by.isnot(None))
        .group_by(User.invited_by)
        .subquery()
    )
    subs = (dev, rep, mnt, inv)
    metrics = tuple(func.coalesce(s.c.n, 0) for s in subs)
    return subs, metrics


def _normalise_sort(sort: str | None) -> str:
    return sort if sort in SORTABLE else DEFAULT_SORT


def _normalise_dir(direction: str | None) -> str:
    return direction if direction in ("asc", "desc") else DEFAULT_DIR


def _name_order(direction: str):
    """Stable tiebreak so members with identical counts do not reorder
    themselves between page loads."""
    if direction == "asc":
        return [Profile.full_name.asc().nulls_last(), Profile.username.asc()]
    return [Profile.full_name.desc().nulls_last(), Profile.username.desc()]


def _order_by(sort: str, direction: str, metrics):
    """The ORDER BY clause. `default` is the composite leaderboard: most
    registrations first, then repairs, then maintenance, then invites."""
    devices_n, repairs_n, maintenance_n, invites_n = metrics

    def d(col):
        return col.desc() if direction == "desc" else col.asc()

    if sort == "devices":
        return [d(devices_n), *_name_order(direction)]
    if sort == "repairs":
        return [d(repairs_n), *_name_order(direction)]
    if sort == "maintenance":
        return [d(maintenance_n), *_name_order(direction)]
    if sort == "invites":
        return [d(invites_n), *_name_order(direction)]
    if sort == "name":
        return _name_order(direction)
    return [
        d(devices_n), d(repairs_n), d(maintenance_n), d(invites_n),
        *_name_order(direction),
    ]


@router.get("/profiles")
async def list_profiles(
    q: Optional[str] = None,
    limit: int = 24,
    offset: int = 0,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    viewer: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Network directory: every active member of the platform.

    `sort` is one of devices|repairs|maintenance|invites|name; anything else
    falls back to the composite leaderboard. `dir` is asc|desc. Both are
    whitelisted rather than interpolated, and echoed back so the UI can mark
    the active column.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    sort = _normalise_sort(sort)
    direction = _normalise_dir(dir)

    subs, metrics = _metric_subqueries()
    base = (
        select(
            Profile,
            metrics[0].label("devices_n"),
            metrics[1].label("repairs_n"),
            metrics[2].label("maintenance_n"),
            metrics[3].label("invites_n"),
        )
        .join(User, User.id == Profile.id)
        .outerjoin(subs[0], subs[0].c.pid == Profile.id)
        .outerjoin(subs[1], subs[1].c.pid == Profile.id)
        .outerjoin(subs[2], subs[2].c.pid == Profile.id)
        .outerjoin(subs[3], subs[3].c.pid == Profile.id)
        .where(User.is_active.is_(True))
    )
    if q and q.strip():
        needle = f"%{q.strip()}%"
        base = base.where(
            Profile.username.ilike(needle) | Profile.full_name.ilike(needle)
        )

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar_one()

    result = await db.execute(
        base.options(
            selectinload(Profile.org_memberships).selectinload(OrgUser.organization)
        )
        .order_by(*_order_by(sort, direction, metrics))
        .limit(limit)
        .offset(offset)
    )

    items = []
    for row in result.all():
        p, dev_n, rep_n, mnt_n, inv_n = row
        items.append(_card(p, {
            "devices_registered": int(dev_n),
            "faults_resolved": int(rep_n),
            "maintenance_performed": int(mnt_n),
            "invites": int(inv_n),
        }))

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "dir": direction,
    }


@router.get("/profiles/{profile_id}")
async def get_profile_view(
    profile_id: uuid.UUID,
    viewer: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    target = await _load_viewable_profile(db, viewer.id, profile_id)
    return {
        "id": target.id,
        "username": target.username,
        "full_name": target.full_name,
        "country": target.country,
        "avatar_key": target.avatar_key,
        # Lets the frontend tell "someone else's profile (read-only)" from
        # "mine" without a second round-trip, so the two never share a page.
        "is_self": target.id == viewer.id,
        # The same four numbers the Network table sorts by, so a member's
        # public page always agrees with their row in the directory.
        **await _counts_for(db, target.id),
        "organizations": [
            {
                "id": m.organization_id,
                "name": m.organization.name if m.organization else None,
                "country": m.organization.country if m.organization else None,
                "role": m.role,
            }
            for m in target.org_memberships
        ],
    }


@router.get("/profiles/{profile_id}/photo")
async def get_profile_view_photo(
    profile_id: uuid.UUID,
    viewer: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    target = await _load_viewable_profile(db, viewer.id, profile_id)
    if not target.avatar_key:
        raise HTTPException(status_code=404, detail="No avatar")
    obj = await get_file(target.avatar_key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Avatar not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)
