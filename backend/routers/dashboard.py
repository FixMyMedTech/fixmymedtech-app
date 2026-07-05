from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db
from utils.profile import get_current_profile
from models.models import Device, FaultReport, MaintenanceLog, Profile

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve estadísticas agregadas para el dashboard admin:
    conteo de dispositivos por estado, fallas abiertas, mantenimiento próximo.
    """
    org_id = profile.organization_id
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=30)

    # ── Conteo de dispositivos por status (agregado en SQL, no en Python) ──
    status_counts_result = await db.execute(
        select(Device.status, func.count(Device.id))
        .where(Device.organization_id == org_id)
        .group_by(Device.status)
    )
    by_status = {"operational": 0, "maintenance": 0, "fault": 0, "decommissioned": 0}
    for status_value, count in status_counts_result.all():
        by_status[status_value] = count

    total = sum(by_status.values())

    # ── Mantenimiento vencido / próximo (agregado en SQL con func.count + case) ──
    maintenance_result = await db.execute(
        select(
            func.count(case((Device.next_maintenance < now.date(), Device.id))),
            func.count(case((
                Device.next_maintenance.between(now.date(), soon.date()), Device.id
            ))),
        ).where(Device.organization_id == org_id)
    )
    overdue_count, due_soon_count = maintenance_result.one()

    # ── Fallas abiertas (con join a Device via relationship) ──
    open_faults_result = await db.execute(
        select(FaultReport)
        .join(Device, FaultReport.device_id == Device.id)
        .options(selectinload(FaultReport.device))
        .where(Device.organization_id == org_id, FaultReport.status == "open")
        .order_by(FaultReport.reported_at.desc())
        .limit(10)
    )
    open_faults = [
        {
            "id": f.id,
            "severity": f.severity,
            "reported_at": f.reported_at,
            "device_name": f.device.name,
            "device_location": f.device.location,
        }
        for f in open_faults_result.scalars().all()
    ]

    # ── Mantenimiento reciente ──
    recent_maintenance_result = await db.execute(
        select(MaintenanceLog)
        .join(Device, MaintenanceLog.device_id == Device.id)
        .options(selectinload(MaintenanceLog.device))
        .where(Device.organization_id == org_id)
        .order_by(MaintenanceLog.performed_at.desc())
        .limit(5)
    )
    recent_maintenance = [
        {
            "id": m.id,
            "performed_at": m.performed_at,
            "type": m.type,
            "device_name": m.device.name,
        }
        for m in recent_maintenance_result.scalars().all()
    ]

    return {
        "total_devices": total,
        "by_status": by_status,
        "maintenance_overdue": overdue_count,
        "maintenance_due_soon": due_soon_count,
        "open_faults": open_faults,
        "recent_maintenance": recent_maintenance,
    }