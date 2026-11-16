from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.db_config import get_db
from utils.profile import get_current_profile
from utils import onboarding as ob
from utils import service as svc
from models.models import Device, FaultReport, MaintenanceLog, Profile

router = APIRouter()

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


async def _device_filter(db, profile: Profile):
    """Same reach as the device list: the caller's organizations (as owner,
    maintainer or healthsite) and the clinics they are responsible for."""
    org_ids = profile.org_ids()
    responsible = await ob.responsible_org_ids(db, profile, profile.user)
    return or_(
        Device.organization_id.in_(org_ids),
        Device.organization_maintenance_id.in_(org_ids),
        Device.healthsite_id.in_(org_ids),
        Device.organization_id.in_(responsible),
        Device.healthsite_id.in_(responsible),
    )


@router.get("/stats")
async def get_dashboard_stats(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    soon = today + timedelta(days=30)
    device_filter = await _device_filter(db, profile)

    status_counts_result = await db.execute(
        select(Device.status, func.count(Device.id))
        .where(device_filter)
        .group_by(Device.status)
    )
    by_status = {"operational": 0, "maintenance": 0, "fault": 0, "decommissioned": 0}
    for status_value, count in status_counts_result.all():
        by_status[status_value] = count

    total = sum(by_status.values())

    maintenance_result = await db.execute(
        select(
            func.count(case((Device.next_maintenance < today, Device.id))),
            func.count(case((Device.next_maintenance.between(today, soon), Device.id))),
        ).where(device_filter, Device.status != "decommissioned")
    )
    overdue_count, due_soon_count = maintenance_result.one()

    open_faults_result = await db.execute(
        select(FaultReport)
        .join(Device, FaultReport.device_id == Device.id)
        .options(selectinload(FaultReport.device))
        .where(device_filter, FaultReport.status.in_(("open", "assigned", "diagnosed", "approved")))
        .order_by(FaultReport.reported_at.desc())
        .limit(50)
    )
    open_faults = [
        {
            "id": f.id,
            "status": f.status,
            "severity": f.severity,
            "description": f.description,
            "reported_at": f.reported_at,
            "device_id": f.device_id,
            "device_name": f.device.name,
            "device_location": f.device.location,
        }
        for f in open_faults_result.scalars().all()
    ]

    recent_maintenance_result = await db.execute(
        select(MaintenanceLog)
        .join(Device, MaintenanceLog.device_id == Device.id)
        .options(selectinload(MaintenanceLog.device))
        .where(device_filter)
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(5)
    )
    recent_maintenance = [
        {
            "id": m.id,
            "performed_at": m.performed_at,
            "type": m.type,
            "status": m.status,
            "device_id": m.device_id,
            "device_name": m.device.name,
        }
        for m in recent_maintenance_result.scalars().all()
    ]

    # "Needs you today": unresolved faults first (worst severity first), then
    # overdue services, then services due within svc.DUE_SOON_DAYS.
    needs = [
        {"kind": "fault", "device_id": f["device_id"], "device_name": f["device_name"],
         "location": f["device_location"], "severity": f["severity"], "date": f["reported_at"],
         "fault_id": f["id"]}
        for f in sorted(open_faults, key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
    ]
    due_rows = (await db.execute(
        select(Device.id, Device.name, Device.location, Device.next_maintenance)
        .where(device_filter, Device.status != "decommissioned",
               Device.next_maintenance <= today + timedelta(days=svc.DUE_SOON_DAYS))
        .order_by(Device.next_maintenance)
    )).all()
    needs += [
        {"kind": svc.service_state(nm, today), "device_id": did, "device_name": name,
         "location": loc, "date": nm}
        for did, name, loc, nm in due_rows
    ]

    return {
        "total_devices": total,
        "by_status": by_status,
        "maintenance_overdue": overdue_count,
        "maintenance_due_soon": due_soon_count,
        "open_faults": open_faults[:10],
        "recent_maintenance": recent_maintenance,
        "needs_you": needs[:20],
        "needs_you_total": len(needs),
    }


@router.post("/reminders/run")
async def run_reminders(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Send due service reminders now (superusers; the backend also does this
    on its own every few hours)."""
    if not (profile.user and profile.user.is_superuser):
        raise HTTPException(status_code=403, detail="Superusers only")
    return await svc.send_due_reminders(db)
