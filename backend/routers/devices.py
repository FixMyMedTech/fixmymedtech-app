# routers/devices.py

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db
from utils.profile import get_current_profile
from models.models import Device, DeviceCategory, Document, MaintenanceLog, FaultReport, Profile

router = APIRouter()

# TODO: Add Pydantic models for request/response schemas
class DeviceCreate(BaseModel):
    id: Optional[UUID] = None
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    category_id: Optional[UUID] = None
    manufacture_year: Optional[int] = None
    acquisition_date: Optional[date] = None
    acquisition_type: Optional[str] = "purchased"
    location: Optional[str] = None
    notes: Optional[str] = None
    next_maintenance: Optional[date] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    next_maintenance: Optional[date] = None


# ── Endpoint público: escaneado vía QR (sin auth) ──────────────
@router.get("/public/{device_id}")
async def get_device_public(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Se llama cuando alguien escanea el QR del dispositivo.
    Devuelve info del device + documentos + fallas recientes.
    No requiere autenticación.
    """
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

    return {
        "device": device,
        "documents": docs,
        "recent_faults": recent_faults,
    }


# ── Endpoints protegidos (requieren auth) ──────────────────────
@router.get("/")
async def list_devices(
    status: Optional[str] = None,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Device)
        .options(selectinload(Device.category))
        .where(Device.organization_id == profile.organization_id)
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

# TODO: Add endpoints for creating, updating, and deleting devices, with proper role-based access control (admin/technician).
# TODO: Handle category_id validation when creating/updating devices (ensure it belongs to the same organization).
@router.post("/")
async def create_device(
    body: DeviceCreate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if profile.role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    payload = body.model_dump(exclude_none=True)
    device = Device(**payload, organization_id=profile.organization_id,organization_maintenance_id=profile.organization_id)
    print(device) 
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
    if profile.role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    payload = body.model_dump(exclude_none=True)
    for key, value in payload.items():
        setattr(device, key, value)

    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}")
async def delete_device(
    device_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if profile.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete devices")

    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    await db.delete(device)
    await db.commit()
    return {"message": "Device deleted"}