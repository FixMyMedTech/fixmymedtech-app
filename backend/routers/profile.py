# routers/profile.py — Profile endpoints (me, avatar, stats)
#
# Mounted under /api/auth, keeping the same frontend contract:
#   GET   /api/auth/me         → {id, username, full_name, country, avatar_key, organizations}
#   PATCH /api/auth/me         → {id, username, full_name, country, avatar_key}
#   POST  /api/auth/me/photo   → {avatar_key, mime_type}
#   GET   /api/auth/me/photo   → avatar image bytes
#   GET   /api/auth/me/stats   → {devices_registered, faults_resolved, maintenance_performed}

import asyncio
import io
import os
import uuid

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File as FileParam
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import select, text, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from models.models import Profile, OrgUser, User, Device, FaultReport, MaintenanceLog
from config.db_config import get_db
from config.storage import upload_file, get_file, delete_file
from config.users import current_active_user

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

    org_ids = profile.org_ids()
    if org_ids:
        devices_count = (
            await db.execute(
                select(func.count(Device.id)).where(or_(
                    Device.organization_id.in_(org_ids),
                    Device.organization_maintenance_id.in_(org_ids),
                ))
            )
        ).scalar_one()
    else:
        devices_count = 0

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