# routers/fault_reports.py
#
# Faults are resolved in steps, each step performed by a different person:
#   1. anyone reports it                                      -> 'open'
#   2. the maintenance-org ADMIN assigns it to a member       -> 'assigned'
#   3. that assignee writes a diagnosis + online quote        -> 'diagnosed'
#   4. the healthsite ADMIN approves or rejects it            -> 'approved' / back to 'assigned'
#      (a device with no healthsite is approved by the maintenance-org admin)
#   5. the assignee repairs it and records the final price    -> 'resolved'
# 'in_progress' is an optional step the assignee can take when they go on site.
#
# Every step records who performed it, so the timeline can show the actor.
#
# NOTE ON SERIALIZATION: Profile.user is lazy="selectin", so a Profile that has
# been loaded carries hashed_password in its __dict__. FastAPI's jsonable_encoder
# walks vars() (it only strips _sa*), so returning ORM rows would leak it. Every
# fault response is therefore built by hand from table columns plus _profile().

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File as FileParam
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.db_config import get_db
from config.storage import get_file, upload_file
from utils.profile import get_current_profile, get_optional_profile
from models.models import Device, FaultReport, Profile, OrgUser

router = APIRouter()

ASSIGNABLE_ROLES = ("technician", "engineering_staff", "admin")


class FaultReportCreate(BaseModel):
    device_id: UUID
    description: str
    severity: str = "medium"
    reporter_name: Optional[str] = None


class FaultStatusUpdate(BaseModel):
    # The reporter (or the assignee) may still correct what was reported.
    # Status, assignee, resolution and price all moved to the step endpoints
    # below — each of those has its own authorization.
    severity: Optional[str] = None
    description: Optional[str] = None


class FaultAssign(BaseModel):
    assigned_to: UUID


class FaultDiagnosis(BaseModel):
    diagnosis: str
    quote_amount: Optional[float] = None
    quote_notes: Optional[str] = None


class FaultApproval(BaseModel):
    approved: bool
    comment: Optional[str] = None


class FaultResolve(BaseModel):
    resolution_notes: str
    final_price: Optional[float] = None


# ── serialization ───────────────────────────────────────────────────────────

def _row(obj) -> dict:
    """Table columns only — never relationships, which is what keeps Profile.user
    (and its hashed_password) out of the response."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _profile(p) -> Optional[dict]:
    if p is None:
        return None
    return {"id": p.id, "username": p.username, "full_name": p.full_name}


def _payload(f: FaultReport) -> dict:
    d = _row(f)
    d["device"] = _row(f.device) if f.device is not None else None
    d["reported_by_profile"] = _profile(f.reported_by_profile)
    d["assigned_to_profile"] = _profile(f.assigned_to_profile)
    d["assigned_by_profile"] = _profile(f.assigned_by_profile)
    d["diagnosed_by_profile"] = _profile(f.diagnosed_by_profile)
    d["approved_by_profile"] = _profile(f.approved_by_profile)
    d["resolved_by_profile"] = _profile(f.resolved_by_profile)
    return d


FAULT_EAGER = (
    selectinload(FaultReport.device),
    selectinload(FaultReport.reported_by_profile),
    selectinload(FaultReport.assigned_to_profile),
    selectinload(FaultReport.assigned_by_profile),
    selectinload(FaultReport.diagnosed_by_profile),
    selectinload(FaultReport.approved_by_profile),
    selectinload(FaultReport.resolved_by_profile),
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _money(value) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value))


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _load_fault(db: AsyncSession, fault_id: UUID) -> FaultReport:
    result = await db.execute(
        select(FaultReport).options(*FAULT_EAGER).where(FaultReport.id == fault_id)
    )
    fault = result.scalar_one_or_none()
    if not fault:
        raise HTTPException(status_code=404, detail="Fault report not found")
    return fault


async def _load_device(db: AsyncSession, device_id) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _can_edit_fault(fault: FaultReport, profile: Profile) -> bool:
    return fault.reported_by == profile.id or fault.assigned_to == profile.id


def _is_assignee(fault: FaultReport, profile: Profile) -> bool:
    return fault.assigned_to is not None and fault.assigned_to == profile.id


def _maint_admin(profile: Profile, device: Device) -> bool:
    return profile.get_role_for_org(device.organization_maintenance_id) == "admin"


def _healthsite_admin(profile: Profile, device: Device) -> bool:
    return bool(device.healthsite_id) and profile.get_role_for_org(device.healthsite_id) == "admin"


def _can_approve(profile: Profile, device: Device) -> bool:
    # A device with no healthsite is approved by the maintenance-org admin.
    if device.healthsite_id:
        return _healthsite_admin(profile, device)
    return _maint_admin(profile, device)


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


# ── public report ────────────────────────────────────────────────────────────

@router.post("/public")
async def submit_fault_public(
    body: FaultReportCreate,
    profile: Optional[Profile] = Depends(get_optional_profile),
    db: AsyncSession = Depends(get_db),
):
    device = await _load_device(db, body.device_id)

    # Assignment is step 2 of the workflow and belongs to the maintenance-org
    # admin, so a report always starts out unassigned.
    fault = FaultReport(
        device_id=body.device_id,
        reported_by=profile.id if profile else None,
        description=body.description,
        severity=body.severity,
        reporter_name=body.reporter_name or "Anonymous",
        status="open",
    )
    db.add(fault)

    if body.severity in ("high", "critical"):
        device.status = "fault"

    await db.commit()
    await db.refresh(fault)

    return {"message": "Fault report submitted. A technician will be notified.", "id": fault.id}


@router.get("/public/{fault_id}")
async def get_fault_public(fault_id: UUID, db: AsyncSession = Depends(get_db)):
    return _payload(await _load_fault(db, fault_id))


@router.get("/public/{fault_id}/photo")
async def get_fault_photo_public(fault_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FaultReport).where(FaultReport.id == fault_id))
    fault = result.scalar_one_or_none()
    if not fault or not fault.photo_key:
        raise HTTPException(status_code=404, detail="No photo")

    obj = await get_file(fault.photo_key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Photo not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)


@router.post("/{fault_id}/photo")
async def upload_fault_photo(
    fault_id: UUID,
    photo: UploadFile = FileParam(...),
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    fault = await _load_fault(db, fault_id)
    if not _can_edit_fault(fault, profile):
        raise HTTPException(status_code=403, detail="Only the reporter or assignee can edit this fault report")

    content = await photo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty photo")

    # Stored as-is: no downscale/white-background processing for fault photos.
    filename = photo.filename or "fault_photo.jpg"
    ctype = photo.content_type or "application/octet-stream"
    key = await upload_file(
        "faults", str(fault_id), filename, content, ctype,
        object_id=f"photo_{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower() or '.jpg'}",
    )
    fault.photo_key = key
    await db.commit()

    return {"photo_key": key, "mime_type": ctype}


@router.get("/{fault_id}/photo")
async def get_fault_photo(
    fault_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FaultReport).where(FaultReport.id == fault_id))
    fault = result.scalar_one_or_none()
    if not fault or not fault.photo_key:
        raise HTTPException(status_code=404, detail="No photo")

    obj = await get_file(fault.photo_key)
    if obj is None:
        raise HTTPException(status_code=404, detail="Photo not found in storage")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)


@router.get("/assignees/{device_id}")
async def get_fault_assignees(
    device_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    device = await _load_device(db, device_id)

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


# ── lists ────────────────────────────────────────────────────────────────────
# NOTE: these sit above GET /{fault_id} on purpose — a static path segment has
# to be registered before the path-parameter route or it gets swallowed.

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
        .options(*FAULT_EAGER)
        .where(or_(
            Device.organization_id.in_(org_ids),
            Device.organization_maintenance_id.in_(org_ids),
        ))
        .order_by(FaultReport.reported_at.desc())
    )

    if status:
        query = query.where(FaultReport.status == status)

    result = await db.execute(query)
    return [_payload(f) for f in result.scalars().all()]


@router.get("/maintained")
async def list_maintained_faults(
    status: Optional[str] = None,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Faults on devices my organizations MAINTAIN (not the ones they own)."""
    org_ids = profile.org_ids()
    query = (
        select(FaultReport)
        .join(Device, FaultReport.device_id == Device.id)
        .options(*FAULT_EAGER)
        .where(Device.organization_maintenance_id.in_(org_ids))
        .order_by(FaultReport.reported_at.desc())
    )

    if status:
        query = query.where(FaultReport.status == status)

    result = await db.execute(query)
    return [_payload(f) for f in result.scalars().all()]


@router.get("/{fault_id}")
async def get_fault(
    fault_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return _payload(await _load_fault(db, fault_id))


# ── workflow steps ───────────────────────────────────────────────────────────

@router.patch("/{fault_id}/assign")
async def assign_fault(
    fault_id: UUID,
    body: FaultAssign,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    fault = await _load_fault(db, fault_id)
    device = await _load_device(db, fault.device_id)

    if not _maint_admin(profile, device):
        raise HTTPException(
            status_code=403,
            detail="Only the admin of the maintenance organization can assign a fault",
        )
    if fault.status not in ("open", "assigned"):
        raise HTTPException(status_code=409, detail="This fault is past the assignment step")

    await _validate_assignee(db, body.assigned_to, device.organization_maintenance_id)

    fault.assigned_to = body.assigned_to
    fault.assigned_by = profile.id
    fault.assigned_at = _now()
    fault.status = "assigned"

    await db.commit()
    return _payload(await _load_fault(db, fault_id))


@router.patch("/{fault_id}/start")
async def start_fault(
    fault_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Optional: the assignee marks the repair as under way when they go on site."""
    fault = await _load_fault(db, fault_id)

    if not _is_assignee(fault, profile):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned technician can start the repair",
        )
    if fault.status != "approved":
        raise HTTPException(
            status_code=409,
            detail="The diagnosis must be approved before the repair can start",
        )

    fault.status = "in_progress"
    await db.commit()
    return _payload(await _load_fault(db, fault_id))


@router.patch("/{fault_id}/diagnosis")
async def submit_fault_diagnosis(
    fault_id: UUID,
    body: FaultDiagnosis,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    fault = await _load_fault(db, fault_id)

    if not _is_assignee(fault, profile):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned technician can submit a diagnosis",
        )
    if fault.status != "assigned":
        raise HTTPException(status_code=409, detail="This fault is not waiting for a diagnosis")

    fault.diagnosis = body.diagnosis
    fault.diagnosed_by = profile.id
    fault.diagnosed_at = _now()
    fault.quote_amount = _money(body.quote_amount)
    fault.quote_notes = body.quote_notes
    fault.status = "diagnosed"
    # Clears a previous rejection when the technician resubmits.
    fault.approval_status = "pending"

    await db.commit()
    return _payload(await _load_fault(db, fault_id))


@router.patch("/{fault_id}/approval")
async def review_fault_approval(
    fault_id: UUID,
    body: FaultApproval,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    fault = await _load_fault(db, fault_id)
    device = await _load_device(db, fault.device_id)

    if not _can_approve(profile, device):
        raise HTTPException(
            status_code=403,
            detail="Only the healthsite admin can approve a diagnosis",
        )
    if fault.status != "diagnosed":
        raise HTTPException(status_code=409, detail="This fault is not waiting for approval")

    comment = (body.comment or "").strip()
    if not body.approved and not comment:
        raise HTTPException(
            status_code=400,
            detail="A comment is required when rejecting a diagnosis",
        )

    fault.approval_status = "approved" if body.approved else "rejected"
    fault.approved_by = profile.id
    fault.approved_at = _now()
    fault.approval_comment = comment or None
    # A rejection sends it back to the assignee, who revises and resubmits.
    fault.status = "approved" if body.approved else "assigned"

    await db.commit()
    return _payload(await _load_fault(db, fault_id))


@router.patch("/{fault_id}/resolve")
async def resolve_fault(
    fault_id: UUID,
    body: FaultResolve,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    fault = await _load_fault(db, fault_id)

    if not _is_assignee(fault, profile):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned technician can complete the repair",
        )
    if fault.status not in ("approved", "in_progress"):
        raise HTTPException(
            status_code=409,
            detail="The diagnosis must be approved before the repair can be completed",
        )

    fault.resolution_notes = body.resolution_notes
    fault.final_price = _money(body.final_price)
    fault.resolved_by = profile.id
    fault.resolved_at = _now()
    fault.status = "resolved"

    await db.commit()
    return _payload(await _load_fault(db, fault_id))


@router.patch("/{fault_id}")
async def update_fault(
    fault_id: UUID,
    body: FaultStatusUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    fault = await _load_fault(db, fault_id)

    if not _can_edit_fault(fault, profile):
        raise HTTPException(status_code=403, detail="Only the reporter or assignee can edit this fault report")

    if body.severity is not None:
        fault.severity = body.severity
    if body.description is not None:
        fault.description = body.description

    await db.commit()
    return _payload(await _load_fault(db, fault_id))
