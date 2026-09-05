# routers/devices.py

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File as FileParam
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.db_config import get_db
from utils.profile import get_current_profile
from models.models import Device, DeviceCategory, Document, MaintenanceLog, FaultReport, Profile
from config.storage import upload_file, get_file
from config.db_config import AsyncSessionLocal
from utils.photo_processing import process_photo_to_white, compress_device_photo
import asyncio
import uuid
import os

router = APIRouter()


class DeviceCreate(BaseModel):
    id: Optional[UUID] = None
    name: str
    organization_id: Optional[UUID] = None
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

    org_id = body.organization_id or profile.org_memberships[0].organization_id
    role = profile.get_role_for_org(org_id)

    if role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    payload = body.model_dump(exclude_none=True)
    payload.pop("organization_id", None)
    device = Device(
        **payload,
        organization_id=org_id,
        organization_maintenance_id=org_id,
        registered_by=profile.id,
    )
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


# ── Photo upload / serve (MinIO via boto3) ────────────────────────────────────

@router.post("/{device_id}/photo")
async def upload_device_photo(
    device_id: UUID,
    photo: UploadFile = FileParam(...),
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

    content = await photo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty photo")

    # Downscale + re-encode before storing so MinIO stays small while the
    # photo keeps enough quality for catalogue / fault-review use.
    content, ctype, filename = await compress_device_photo(
        content,
        photo.content_type or "application/octet-stream",
        photo.filename or "device_photo.jpg",
    )

    original_key = await upload_file(
        "devices", str(device_id), filename, content, ctype,
        object_id=f"raw_{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower() or '.jpg'}",
    )
    device.photo_key = original_key
    await db.commit()

    # Never block registration on background cleanup — process off the
    # request path so the submit returns immediately (see AC4 pattern).
    asyncio.create_task(
        _process_device_photo(device_id, original_key, ctype, filename)
    )
    return {"photo_key": original_key, "mime_type": ctype}


async def _process_device_photo(device_id: UUID, original_key: str, mime_type: str, filename: str):
    """Background task: whiten the background of a just-uploaded device photo.

    Best-effort and never raising — if processing fails, the original is kept
    and the worker logs the reason.
    """
    try:
        obj = await get_file(original_key)
        if obj is None:
            return
        content, _ = obj

        processed = await process_photo_to_white(content, mime_type, filename)
        if processed is None:
            return

        pbytes, pmime, pname = processed
        base = original_key.rsplit("/", 1)[-1]
        if base.startswith("raw_"):
            processed_object = "processed_" + base[len("raw_"):]
            processed_key = await upload_file(
                "devices", str(device_id), processed_object, pbytes, pmime,
                object_id=processed_object,
            )
        else:
            processed_key = await upload_file("devices", str(device_id), pname, pbytes, pmime)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()
            if device is None:
                return
            device.photo_processed_key = processed_key
            await db.commit()
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger("devices.photo").warning(
            "background photo processing failed for %s: %s", device_id, e
        )


@router.get("/{device_id}/photo")
async def get_device_photo(
    device_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device or not device.photo_key:
        raise HTTPException(status_code=404, detail="No photo")

    role = profile.get_role_for_org(device.organization_id)
    if role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Not authorized")

    key = device.photo_processed_key or device.photo_key
    obj = await get_file(key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Photo not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)
