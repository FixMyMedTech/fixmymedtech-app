# utils/profile.py — resolve the current user from a FastAPI-Users JWT
#
# Uses FastAPI-Users' JWTStrategy for token validation, then loads the
# Profile with org_memberships for the rest of the application.

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config.db_config import get_db
from config.users import current_active_user
from models.models import User, Profile, OrgUser


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
