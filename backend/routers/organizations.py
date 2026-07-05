# routers/organizations.py

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.supabase_config import get_db
from models.models import Organization

router = APIRouter()


@router.get("/")
async def list_organizations(db: AsyncSession = Depends(get_db)):
    """Endpoint público — necesario para el dropdown del formulario de signup."""
    result = await db.execute(select(Organization).order_by(Organization.name))
    return result.scalars().all()