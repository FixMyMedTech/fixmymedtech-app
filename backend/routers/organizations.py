# routers/organizations.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.profile import get_current_profile
from config.supabase_config import get_db
from models.models import Organization, Profile, OrgUser

router = APIRouter()


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[str] = None


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


@router.patch("/{org_id}")
async def update_organization(
    org_id: str,
    body: OrgUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    role = profile.get_role_for_org(org_uuid)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit organizations")

    result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if body.name is not None:
        org.name = body.name
    if body.country is not None:
        org.country = body.country
    if body.contact_email is not None:
        org.contact_email = body.contact_email

    await db.commit()
    await db.refresh(org)
    return {
        "id": str(org.id),
        "name": org.name,
        "country": org.country,
        "contact_email": org.contact_email,
    }
