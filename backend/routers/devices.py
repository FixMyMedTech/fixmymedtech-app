# routers/devices.py

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db
from utils.profile import get_current_profile
from models.models import Device, DeviceCategory, Document, MaintenanceLog, FaultReport, Profile

router = APIRouter()


class DeviceCreate(BaseModel):
    id: Optional[UUID] = None
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    category_id: Optional[str] = None
    manufacture_year: Optional[int] = None
    acquisition_date: Optional[date] = None
    acquisition_type: Optional[str] = "purchased"
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    next_maintenance: Optional[date] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    next_maintenance: Optional[date] = None
    organization_maintenance_id: Optional[UUID] = None


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float


@router.get("/public/{device_id}")
async def get_device_public(device_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Device)
        .options(
            selectinload(Device.category),
            selectinload(Device.organization),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    docs_result = await db.execute(
        select(Document).where(Document.device_id == device_id)
    )
    docs = docs_result.scalars().all()

    faults_result = await db.execute(
        select(FaultReport)
        .where(FaultReport.device_id == device_id)
        .order_by(FaultReport.reported_at.desc())
        .limit(5)
    )
    recent_faults = faults_result.scalars().all()

    logs_result = await db.execute(
        select(MaintenanceLog)
        .options(selectinload(MaintenanceLog.performed_by_profile))
        .where(MaintenanceLog.device_id == device_id)
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(5)
    )
    recent_logs = logs_result.scalars().all()

    return {
        "device": device,
        "documents": docs,
        "recent_faults": recent_faults,
        "recent_logs": recent_logs,
    }


@router.get("/")
async def list_devices(
    status: Optional[str] = None,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    org_ids = profile.org_ids()
    query = (
        select(Device)
        .options(
            selectinload(Device.category),
            selectinload(Device.organization_maintenance),
        )
        .where(or_(
            Device.organization_id.in_(org_ids),
            Device.organization_maintenance_id.in_(org_ids),
        ))
        .order_by(Device.name)
    )

    if status:
        query = query.where(Device.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeviceCategory)
        .order_by(DeviceCategory.name)
    )
    return result.scalars().all()


@router.get("/{device_id}")
async def get_device(
    device_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    device_result = await db.execute(
        select(Device)
        .options(
            selectinload(Device.category),
            selectinload(Device.organization),
        )
        .where(Device.id == device_id)
    )
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    logs_result = await db.execute(
        select(MaintenanceLog)
        .options(selectinload(MaintenanceLog.performed_by_profile))
        .where(MaintenanceLog.device_id == device_id)
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(10)
    )
    logs = logs_result.scalars().all()

    faults_result = await db.execute(
        select(FaultReport)
        .options(selectinload(FaultReport.assigned_to_profile))
        .where(FaultReport.device_id == device_id)
        .order_by(FaultReport.reported_at.desc())
        .limit(10)
    )
    faults = faults_result.scalars().all()

    docs_result = await db.execute(
        select(Document).where(Document.device_id == device_id)
    )
    docs = docs_result.scalars().all()

    return {
        "device": device,
        "maintenance_logs": logs,
        "fault_reports": faults,
        "documents": docs,
    }


@router.post("/")
async def create_device(
    body: DeviceCreate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if not profile.org_memberships:
        raise HTTPException(status_code=403, detail="No organization membership")

    primary_org = profile.org_memberships[0].organization_id
    primary_role = profile.org_memberships[0].role

    if primary_role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    payload = body.model_dump(exclude_none=True)
    device = Device(**payload, organization_id=primary_org, organization_maintenance_id=primary_org)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.patch("/{device_id}")
async def update_device(
    device_id: UUID,
    body: DeviceUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    role = profile.get_role_for_org(device.organization_id)
    if role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    if body.organization_maintenance_id is not None:
        if role != "admin" or device.organization_id not in profile.org_ids():
            raise HTTPException(status_code=403, detail="Only the admin of the organization owning the device can change the maintenance organization")

    payload = body.model_dump(exclude_none=True)
    for key, value in payload.items():
        setattr(device, key, value)

    await db.commit()
    await db.refresh(device)
    return device


@router.patch("/{device_id}/location")
async def update_device_location(
    device_id: UUID,
    body: LocationUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.latitude = body.latitude
    device.longitude = body.longitude
    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}")
async def delete_device(
    device_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    role = profile.get_role_for_org(device.organization_id)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete devices")

    await db.delete(device)
    await db.commit()
    return {"message": "Device deleted"}
