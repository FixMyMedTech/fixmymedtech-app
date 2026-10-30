# utils/profile.py — resolve the current user from a FastAPI-Users JWT
#
# Uses FastAPI-Users' JWTStrategy for token validation, then loads the
# Profile with org_memberships for the rest of the application.

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config.db_config import get_db
from config.users import current_active_user, fastapi_users
from models.models import User, Profile, OrgUser

current_optional_user = fastapi_users.current_user(optional=True)


async def get_current_profile(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """Return the Profile for the authenticated user (with org memberships loaded)."""
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships).selectinload(OrgUser.organization))
        .where(Profile.id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.org_memberships:
        raise HTTPException(status_code=403, detail="User has no organization assigned")

    return profile


async def get_optional_profile(
    user: User | None = Depends(current_optional_user),
    db: AsyncSession = Depends(get_db),
) -> Profile | None:
    if user is None:
        return None
    result = await db.execute(select(Profile).where(Profile.id == user.id))
    return result.scalar_one_or_none()


# ── Community gate (migration 029) ─────────────────────────────────────────
#
# Attached to every platform router in main.py. A signed-in account that is
# still a community applicant (doing the welcome quests) or was refused gets
# 403 {"detail": "community_access_pending"}; members, invited clinic staff
# and superusers pass. Anonymous calls pass through untouched, so public
# /public/... endpoints and each route's own auth keep working.
#
# The profile, Discord, community and auth routes are NOT gated, so an
# applicant can still do their quests.

PLATFORM_STATUSES = ("member", "staff")


async def require_platform_access(
    request: Request,
    user: User | None = Depends(current_optional_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user is None or user.is_superuser:
        return
    # Public QR pages and public fault reports stay open to everyone, even
    # when the browser happens to carry an applicant's token.
    if "/public" in request.url.path:
        return
    status = await db.scalar(select(Profile.member_status).where(Profile.id == user.id))
    if status is None or status in PLATFORM_STATUSES:
        from utils.community import touch_activity
        await touch_activity(db, user.id)
        await db.commit()
        return
    raise HTTPException(status_code=403, detail="community_access_pending")
