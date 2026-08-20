# routers/maintenance_logs.py

from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db
from utils.profile import get_current_profile
from models.models import Device, MaintenanceLog, Profile, OrgUser

router = APIRouter()

ASSIGNABLE_ROLES = ("technician", "engineering_staff", "admin")
LOG_TYPES = ("preventive", "corrective", "inspection")
LOG_STATUSES = ("open", "in_progress", "closed")


@router.get("/{log_id}")
async def get_maintenance_log(
    log_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MaintenanceLog)
        .options(
            selectinload(MaintenanceLog.device),
            selectinload(MaintenanceLog.performed_by_profile),
            selectinload(MaintenanceLog.assigned_to_profile),
        )
        .where(MaintenanceLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Maintenance log not found")
    return log


@router.get("/public/{log_id}")
async def get_maintenance_log_public(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MaintenanceLog)
        .options(
            selectinload(MaintenanceLog.device),
            selectinload(MaintenanceLog.performed_by_profile),
            selectinload(MaintenanceLog.assigned_to_profile),
        )
        .where(MaintenanceLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Maintenance log not found")
    return log


class MaintenanceLogCreate(BaseModel):
    device_id: UUID
    type: str = "preventive"
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None


class MaintenanceLogUpdate(BaseModel):
    type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    parts_replaced: Optional[str] = None
    cost_usd: Optional[float] = None
    next_due: Optional[date] = None


async def _validate_assignee(db: AsyncSession, assignee_id: UUID, org_id: UUID):
    assignee_result = await db.execute(
        select(Profile).where(Profile.id == assignee_id)
    )
    assignee = assignee_result.scalar_one_or_none()
    if not assignee:
        raise HTTPException(status_code=400, detail="Assignee not found")

    assignee_role = assignee.get_role_for_org(org_id)
    if not assignee_role or assignee_role not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Assignee must be a technician or engineer of the maintenance organization",
        )
    return assignee


@router.patch("/{log_id}")
async def update_maintenance_log(
    log_id: UUID,
    body: MaintenanceLogUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MaintenanceLog).where(MaintenanceLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Maintenance log not found")

    device_result = await db.execute(select(Device).where(Device.id == log.device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    role = profile.get_role_for_org(device.organization_id)
    if role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    if body.type is not None:
        if body.type not in LOG_TYPES:
            raise HTTPException(status_code=400, detail=f"Type must be one of {LOG_TYPES}")
        log.type = body.type

    if body.status is not None:
        if body.status not in LOG_STATUSES:
            raise HTTPException(status_code=400, detail=f"Status must be one of {LOG_STATUSES}")
        log.status = body.status

    if body.description is not None:
        log.description = body.description

    if body.parts_replaced is not None:
        log.parts_replaced = body.parts_replaced

    if body.cost_usd is not None:
        log.cost_usd = body.cost_usd

    if body.next_due is not None:
        log.next_due = body.next_due

    if body.assigned_to is not None:
        await _validate_assignee(db, body.assigned_to, device.organization_maintenance_id)
        log.assigned_to = body.assigned_to

    await db.commit()
    await db.refresh(log)
    return log


@router.post("/")
async def create_maintenance_log(
    body: MaintenanceLogCreate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if body.type not in LOG_TYPES:
        raise HTTPException(status_code=400, detail=f"Type must be one of {LOG_TYPES}")

    device_result = await db.execute(select(Device).where(Device.id == body.device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if body.assigned_to:
        await _validate_assignee(db, body.assigned_to, device.organization_maintenance_id)

    log = MaintenanceLog(
        device_id=body.device_id,
        type=body.type,
        description=body.description,
        assigned_to=body.assigned_to,
        performed_at=datetime.now(timezone.utc),
        status="open",
    )
    db.add(log)

    if device.status == "operational":
        device.status = "maintenance"

    await db.commit()
    await db.refresh(log)
    return log
