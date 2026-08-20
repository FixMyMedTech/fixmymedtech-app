# routers/organizations.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.profile import get_current_profile
from config.supabase_config import get_db
from models.models import Organization, Profile, OrgUser

router = APIRouter()


@router.get("/")
async def list_organizations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).order_by(Organization.name))
    return result.scalars().all()


@router.get("/my_organizations")
async def get_my_organizations(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Organization)
        .join(OrgUser, OrgUser.organization_id == Organization.id)
        .where(OrgUser.profile_id == profile.id)
        .order_by(Organization.name)
    )
    orgs = result.scalars().all()
    if not orgs:
        raise HTTPException(status_code=403, detail="No organizations found")
    return orgs
