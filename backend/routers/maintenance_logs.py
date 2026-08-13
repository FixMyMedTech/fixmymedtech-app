# routers/maintenance_logs.py

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.supabase_config import get_db
from utils.profile import get_current_profile
from models.models import Device, MaintenanceLog, Profile

router = APIRouter()

ASSIGNABLE_ROLES = ("technician", "engineering_staff", "admin")
LOG_TYPES = ("preventive", "corrective", "inspection")


class MaintenanceLogCreate(BaseModel):
    device_id: UUID
    type: str = "preventive"
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None


@router.post("/")
async def create_maintenance_log(
    body: MaintenanceLogCreate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Inicia un registro de mantenimiento para un dispositivo.
    Puede asignarse a un técnico/ingeniero de la org de mantenimiento."""

    if body.type not in LOG_TYPES:
        raise HTTPException(status_code=400, detail=f"Type must be one of {LOG_TYPES}")

    device_result = await db.execute(select(Device).where(Device.id == body.device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if body.assigned_to:
        assignee_result = await db.execute(
            select(Profile).where(Profile.id == body.assigned_to)
        )
        assignee = assignee_result.scalar_one_or_none()
        if (
            not assignee
            or assignee.organization_id != device.organization_maintenance_id
            or assignee.role not in ASSIGNABLE_ROLES
        ):
            raise HTTPException(
                status_code=400,
                detail="Assignee must be a technician or engineer of the maintenance organization",
            )

    log = MaintenanceLog(
        device_id=body.device_id,
        type=body.type,
        description=body.description,
        assigned_to=body.assigned_to,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(log)

    # La actividad de mantenimiento empieza: el device pasa a maintenance
    if device.status == "operational":
        device.status = "maintenance"

    await db.commit()
    await db.refresh(log)
    return log
