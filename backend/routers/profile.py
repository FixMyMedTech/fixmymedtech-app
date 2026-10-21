# routers/profile.py — Profile endpoints (me, avatar, stats, network directory)
#
# Mounted under /api/auth, keeping the same frontend contract:
#   GET   /api/auth/me         → {id, username, full_name, country, avatar_key, organizations}
#   PATCH /api/auth/me         → {id, username, full_name, country, avatar_key}
#   POST  /api/auth/me/photo   → {avatar_key, mime_type}
#   GET   /api/auth/me/photo   → avatar image bytes
#   GET   /api/auth/me/stats   → {devices_registered, faults_resolved, maintenance_performed}
#   GET   /api/auth/profiles   → {items, total, limit, offset}  (network directory)
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
    return {
        "id": profile.id,
        "username": profile.username,
        "full_name": profile.full_name,
        "country": profile.country,
        "avatar_key": profile.avatar_key,
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

@router.get("/me/stats")
async def get_profile_stats(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships))
        .where(Profile.id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    devices_count = (
        await db.execute(
            select(func.count(Device.id)).where(Device.registered_by == profile.id)
        )
    ).scalar_one()

    faults_resolved = (
        await db.execute(
            select(func.count(FaultReport.id)).where(
                FaultReport.assigned_to == profile.id,
                FaultReport.status == "resolved",
            )
        )
    ).scalar_one()

    maintenance_performed = (
        await db.execute(
            select(func.count(MaintenanceLog.id)).where(
                MaintenanceLog.performed_by == profile.id
            )
        )
    ).scalar_one()

    return {
        "devices_registered": devices_count,
        "faults_resolved": faults_resolved,
        "maintenance_performed": maintenance_performed,
    }


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


def _card(p: Profile) -> dict:
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
    }


@router.get("/profiles")
async def list_profiles(
    q: Optional[str] = None,
    limit: int = 24,
    offset: int = 0,
    viewer: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Network directory: every active member of the platform."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    base = (
        select(Profile)
        .join(User, User.id == Profile.id)
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
        .order_by(Profile.full_name.asc().nulls_last(), Profile.username.asc())
        .limit(limit)
        .offset(offset)
    )
    items = [_card(p) for p in result.scalars().all()]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
