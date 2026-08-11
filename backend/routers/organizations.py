# routers/organizations.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from utils.profile import get_current_profile
from config.supabase_config import get_db
from models.models import Organization, Profile

router = APIRouter()


@router.get("/")
async def list_organizations(db: AsyncSession = Depends(get_db)):
    """Endpoint público — necesario para el dropdown del formulario de signup."""
    result = await db.execute(select(Organization).order_by(Organization.name))
    return result.scalars().all()


@router.get("/my_organizations")
async def get_my_organizations(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    org_id = profile.organization_id

    try:
        result = await db.execute(
            select(Organization)
            .where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()
        if not organization:
            raise HTTPException(status_code=403, detail="Organization not found")
        return organization
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))