# routers/devices.py

from utils.serialize import device_out, log_out, fault_brief
from utils import service as svc
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File as FileParam
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.db_config import get_db
from utils.profile import get_current_profile
from models.models import (
    Device, DeviceCategory, MaintenanceLog, FaultReport, Profile,
)
from utils import onboarding as ob
from config.storage import upload_file, get_file
from config.db_config import AsyncSessionLocal
from config.discord import welcome_enabled
from routers.discord_link import announce_new_device
from routers.documents import device_documents
from utils.background import spawn
from utils.photo_processing import process_photo_to_white, compress_device_photo
import asyncio
import uuid
import os

router = APIRouter()


add_months = svc.add_months


class DeviceCreate(BaseModel):
    id: Optional[UUID] = None
    name: str
    organization_id: Optional[UUID] = None
    healthsite_id: Optional[UUID] = None
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
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    service_interval_months: Optional[int] = Field(default=None, ge=1, le=60)


DEVICE_STATUSES = ("operational", "maintenance", "fault", "decommissioned")
ACQUISITION_TYPES = ("purchased", "donated", "leased")


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    manufacture_year: Optional[int] = None
    category_id: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    service_interval_months: Optional[int] = Field(default=None, ge=1, le=60)
    acquisition_date: Optional[date] = None
    acquisition_type: Optional[str] = None
    healthsite_id: Optional[UUID] = None
    organization_maintenance_id: Optional[UUID] = None


def _can_manage_device(profile: Profile, device: Device) -> bool:
    """Destructive rights on a device (delete): admin of the owning
    organization, admin of the device's healthsite, or the user who
    registered it. Deliberately excludes the maintaining organization —
    a maintenance contract is not ownership."""
    if profile.get_role_for_org(device.organization_id) == "admin":
        return True
    if device.healthsite_id and profile.get_role_for_org(device.healthsite_id) == "admin":
        return True
    return device.registered_by is not None and device.registered_by == profile.id


def _can_edit_device(profile: Profile, device: Device) -> bool:
    """Edit rights on a device: everyone who can manage it, plus the admin of
    the organization that maintains it. The maintaining organization services
    the device and reports faults on it, so its admin has to be able to
    correct the record — otherwise a mis-assigned device is permanently
    invisible to the people actually working on it."""
    if _can_manage_device(profile, device):
        return True
    return bool(device.organization_maintenance_id) and \
        profile.get_role_for_org(device.organization_maintenance_id) == "admin"


def _can_set_maintenance_org(profile: Profile, device: Device) -> bool:
    """Who may reassign which organization maintains a device: the admin of
    the owning organization, the admin of its healthsite (the customer picks
    who services its equipment), or the admin of the organization currently
    maintaining it (so a mis-assignment can always be corrected)."""
    for org_id in (device.organization_id,
                   device.healthsite_id,
                   device.organization_maintenance_id):
        if org_id and profile.get_role_for_org(org_id) == "admin":
            return True
    return False


def _can_manage_media(profile: Profile, device: Device) -> bool:
    """Photo/location rights: everyone who can manage the device, plus the
    technicians of the owning organization (who maintain it day to day)."""
    if profile.get_role_for_org(device.organization_id) == "technician":
        return True
    return _can_manage_device(profile, device)


def _device_payload(device: Device) -> dict:
    """Scalar columns only, by hand. Returning the ORM object makes
    jsonable_encoder walk the lazy relationships (organization,
    organization_maintenance, healthsite, category), which lazy-loads on an
    async session and turns a successful commit into a 500."""
    return {
        "id": str(device.id),
        "organization_id": str(device.organization_id),
        "organization_maintenance_id": str(device.organization_maintenance_id),
        "healthsite_id": str(device.healthsite_id) if device.healthsite_id else None,
        "category_id": device.category_id,
        "name": device.name,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "serial_number": device.serial_number,
        "manufacture_year": device.manufacture_year,
        "acquisition_date": device.acquisition_date,
        "acquisition_type": device.acquisition_type,
        "location": device.location,
        "latitude": device.latitude,
        "longitude": device.longitude,
        "status": device.status,
        "registered_by": str(device.registered_by) if device.registered_by else None,
        "last_maintenance": device.last_maintenance,
        "next_maintenance": device.next_maintenance,
        "service_interval_months": device.service_interval_months,
        "notes": device.notes,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
    }


class PhotoVariantUpdate(BaseModel):
    variant: str


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
            selectinload(Device.healthsite),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    docs = await device_documents(db, device_id)

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
        "device": device_out(device),
        "documents": docs,
        "recent_faults": [fault_brief(f) for f in recent_faults],
        "recent_logs": [log_out(l) for l in recent_logs],
    }


@router.get("/public/{device_id}/photo")
async def get_device_photo_public(device_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device or not device.photo_key:
        raise HTTPException(status_code=404, detail="No photo")

    key = device.photo_key if device.photo_public_variant == "original" else (
        device.photo_processed_key or device.photo_key
    )
    obj = await get_file(key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Photo not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)


@router.get("/")
async def list_devices(
    status: Optional[str] = None,
    healthsite_id: Optional[UUID] = None,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    # Members of the device's organizations, plus the responsible engineers
    # of its clinic (confirmed, quests done, clinic active).
    org_ids = profile.org_ids()
    responsible = await ob.responsible_org_ids(db, profile, profile.user)
    query = (
        select(Device)
        .options(
            selectinload(Device.category),
            selectinload(Device.organization),
            selectinload(Device.organization_maintenance),
            selectinload(Device.healthsite),
        )
        .where(or_(
            Device.organization_id.in_(org_ids),
            Device.organization_maintenance_id.in_(org_ids),
            Device.healthsite_id.in_(org_ids),
            Device.organization_id.in_(responsible),
            Device.healthsite_id.in_(responsible),
        ))
        .order_by(Device.name)
    )

    if status:
        query = query.where(Device.status == status)
    if healthsite_id:
        query = query.where(Device.healthsite_id == healthsite_id)

    result = await db.execute(query)
    return [device_out(d) for d in result.scalars().all()]


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
            selectinload(Device.organization_maintenance),
            selectinload(Device.healthsite),
        )
        .where(Device.id == device_id)
    )
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not await _can_view_device(db, profile, device):
        raise HTTPException(status_code=403, detail="Not authorized")

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

    docs = await device_documents(db, device_id)

    # Built by hand and returned alongside the device rather than loaded onto
    # it: Profile links to User with lazy="selectin", so eager-loading the
    # relationship would leave hashed_password reachable once FastAPI walks
    # vars() over the instance.
    registrant = None
    if device.registered_by:
        reg_result = await db.execute(
            select(Profile).where(Profile.id == device.registered_by)
        )
        reg = reg_result.scalar_one_or_none()
        if reg:
            registrant = {
                "id": reg.id,
                "username": reg.username,
                "full_name": reg.full_name,
            }

    return {
        "device": device_out(device),
        "maintenance_logs": [log_out(l) for l in logs],
        "fault_reports": [fault_brief(f) for f in faults],
        "documents": docs,
        "registered_by_profile": registrant,
        "service": {
            "interval_months": svc.interval_months(device, device.category),
            "category_interval_months": svc.interval_months(Device(), device.category),
            "state": svc.service_state(device.next_maintenance),
        },
    }


async def _can_view_device(db: AsyncSession, profile: Profile, device: Device) -> bool:
    """The private device page: members of any of the device's three
    organizations, the user who registered it, the clinic's responsible
    engineers (confirmed, quests done, clinic active) and superusers. Everyone
    else has the public QR page."""
    if profile.user is not None and profile.user.is_superuser:
        return True
    if device.registered_by == profile.id:
        return True
    mine = set(profile.org_ids())
    if {device.organization_id, device.organization_maintenance_id, device.healthsite_id} & mine:
        return True
    responsible = set(await ob.responsible_org_ids(db, profile, profile.user))
    return bool({device.organization_id, device.healthsite_id} & responsible)


@router.post("/")
async def create_device(
    body: DeviceCreate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    # Registering for a clinic (migration 030): its own admins, or its
    # confirmed responsible engineers whose welcome quests are done, once the
    # clinic is active. A pending join request no longer allows it.
    org_id = body.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="choose_clinic")

    for target in {org_id, body.healthsite_id} - {None}:
        allowed, reason = await ob.registration_check(db, profile, target, profile.user)
        if not allowed:
            raise HTTPException(status_code=403, detail=f"registration_locked:{reason}")

    payload = body.model_dump(exclude_none=True)
    payload.pop("organization_id", None)
    if "next_maintenance" not in payload:
        months = payload.get("service_interval_months") or await svc.category_interval(db, payload.get("category_id"))
        payload["next_maintenance"] = add_months(date.today(), months)
    device = Device(
        **payload,
        organization_id=org_id,
        organization_maintenance_id=org_id,
        registered_by=profile.id,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    if welcome_enabled():
        spawn(announce_new_device(profile.id))
    return device_out(device)


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

    if not _can_edit_device(profile, device):
        raise HTTPException(status_code=403, detail="Not authorized")

    if body.organization_maintenance_id is not None:
        if not _can_set_maintenance_org(profile, device):
            raise HTTPException(status_code=403, detail="Only the admin of the owning organization, of the healthsite, or of the organization currently maintaining the device can change the maintenance organization")

    payload = body.model_dump(exclude_unset=True)
    if payload.get("status") is not None and payload["status"] not in DEVICE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if payload.get("acquisition_type") is not None and payload["acquisition_type"] not in ACQUISITION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid acquisition type")
    # organization_maintenance_id is NOT NULL — clear requests are ignored.
    if payload.get("organization_maintenance_id") is None:
        payload.pop("organization_maintenance_id", None)
    for key, value in payload.items():
        setattr(device, key, value)

    await db.commit()
    await db.refresh(device)
    return _device_payload(device)


@router.post("/{device_id}/photo-variant")
async def update_device_photo_variant(
    device_id: UUID,
    body: PhotoVariantUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if body.variant not in ("processed", "original"):
        raise HTTPException(status_code=400, detail="Invalid photo variant")

    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if not _can_manage_media(profile, device):
        raise HTTPException(status_code=403, detail="Not authorized")

    device.photo_public_variant = body.variant
    await db.commit()
    await db.refresh(device)
    return {"photo_public_variant": device.photo_public_variant}


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

    if not _can_manage_media(profile, device):
        raise HTTPException(status_code=403, detail="Not authorized")

    device.latitude = body.latitude
    device.longitude = body.longitude
    await db.commit()
    await db.refresh(device)
    return _device_payload(device)


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

    if not _can_manage_device(profile, device):
        raise HTTPException(status_code=403, detail="Only the admin of the owning organization, an admin of its healthsite, or the registering user can delete devices")

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

    if not _can_manage_media(profile, device):
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

    if not _can_manage_media(profile, device):
        raise HTTPException(status_code=403, detail="Not authorized")

    key = device.photo_key if device.photo_public_variant == "original" else (
        device.photo_processed_key or device.photo_key
    )
    obj = await get_file(key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Photo not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)
