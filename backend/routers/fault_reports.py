# routers/fault_reports.py

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db
from utils.profile import get_current_profile
from models.models import Device, FaultReport, Profile, OrgUser

router = APIRouter()

ASSIGNABLE_ROLES = ("technician", "engineering_staff", "admin")


class FaultReportCreate(BaseModel):
    device_id: UUID
    description: str
    severity: str = "medium"
    reporter_name: Optional[str] = None
    assigned_to: Optional[UUID] = None


class FaultStatusUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_to: Optional[UUID] = None


async def _validate_assignee(db: AsyncSession, assignee_id: UUID, org_id: UUID):
    assignee_result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships))
        .where(Profile.id == assignee_id)
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


@router.post("/public")
async def submit_fault_public(body: FaultReportCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == body.device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if body.assigned_to:
        await _validate_assignee(db, body.assigned_to, device.organization_maintenance_id)

    fault = FaultReport(
        device_id=body.device_id,
        description=body.description,
        severity=body.severity,
        reporter_name=body.reporter_name or "Anonymous",
        status="assigned" if body.assigned_to else "open",
        assigned_to=body.assigned_to,
    )
    db.add(fault)

    if body.severity in ("high", "critical"):
        device.status = "fault"

    await db.commit()
    await db.refresh(fault)

    return {"message": "Fault report submitted. A technician will be notified.", "id": fault.id}


@router.get("/public/{fault_id}")
async def get_fault_public(fault_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FaultReport)
        .options(
            selectinload(FaultReport.device),
            selectinload(FaultReport.assigned_to_profile),
            selectinload(FaultReport.reported_by_profile),
        )
        .where(FaultReport.id == fault_id)
    )
    fault = result.scalar_one_or_none()
    if not fault:
        raise HTTPException(status_code=404, detail="Fault report not found")
    return fault


@router.get("/assignees/{device_id}")
async def get_fault_assignees(
    device_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    device_result = await db.execute(select(Device).where(Device.id == device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    result = await db.execute(
        select(Profile, OrgUser.role)
        .join(OrgUser, OrgUser.profile_id == Profile.id)
        .where(
            OrgUser.organization_id == device.organization_maintenance_id,
            OrgUser.role.in_(ASSIGNABLE_ROLES),
        )
        .order_by(Profile.full_name)
    )
    return [
        {"id": p.id, "full_name": p.full_name, "role": role}
        for p, role in result.all()
    ]


@router.get("/")
async def list_faults(
    status: Optional[str] = None,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    org_ids = profile.org_ids()
    query = (
        select(FaultReport)
        .join(Device, FaultReport.device_id == Device.id)
        .options(
            selectinload(FaultReport.device),
            selectinload(FaultReport.assigned_to_profile),
        )
        .where(or_(
            Device.organization_id.in_(org_ids),
            Device.organization_maintenance_id.in_(org_ids),
        ))
        .order_by(FaultReport.reported_at.desc())
    )

    if status:
        query = query.where(FaultReport.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{fault_id}")
async def get_fault(
    fault_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FaultReport)
        .options(
            selectinload(FaultReport.device),
            selectinload(FaultReport.assigned_to_profile),
            selectinload(FaultReport.reported_by_profile),
        )
        .where(FaultReport.id == fault_id)
    )
    fault = result.scalar_one_or_none()
    if not fault:
        raise HTTPException(status_code=404, detail="Fault report not found")
    return fault


@router.patch("/{fault_id}")
async def update_fault(
    fault_id: UUID,
    body: FaultStatusUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FaultReport).where(FaultReport.id == fault_id))
    fault = result.scalar_one_or_none()
    if not fault:
        raise HTTPException(status_code=404, detail="Fault report not found")

    device_result = await db.execute(select(Device).where(Device.id == fault.device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    role = profile.get_role_for_org(device.organization_id)
    if role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    if body.status is not None:
        fault.status = body.status
        if body.status == "resolved":
            fault.resolved_at = datetime.now(timezone.utc)

    if body.severity is not None:
        fault.severity = body.severity

    if body.description is not None:
        fault.description = body.description

    if body.resolution_notes is not None:
        fault.resolution_notes = body.resolution_notes

    if body.assigned_to is not None:
        await _validate_assignee(db, body.assigned_to, device.organization_maintenance_id)
        fault.assigned_to = body.assigned_to
        if fault.status == "open":
            fault.status = "assigned"

    await db.commit()

    # Re-fetch with eager-loaded relationships for safe serialization
    result = await db.execute(
        select(FaultReport)
        .options(
            selectinload(FaultReport.device),
            selectinload(FaultReport.assigned_to_profile),
            selectinload(FaultReport.reported_by_profile),
        )
        .where(FaultReport.id == fault_id)
    )
    return result.scalar_one()
