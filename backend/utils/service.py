# utils/service.py — service plans and reminders (wave 2, migration 031).
#
# A device's service interval is its own override, else its category's, else
# DEFAULT_INTERVAL_MONTHS. Closing a maintenance log rolls the next service
# date forward (roll_forward). send_due_reminders emails each clinic's admins
# and confirmed responsible engineers once per due date: DUE_SOON_DAYS before,
# and once more when the date has passed. Disable the background loop with
# MAINTENANCE_REMINDERS=off.

import asyncio
import calendar
import logging
import os
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from models.models import (
    Device, DeviceCategory, MaintenanceLog, MaintenanceReminder, OrgUser,
    Profile, ResponsibleEngineer, User,
)

logger = logging.getLogger("service")

DEFAULT_INTERVAL_MONTHS = 6
DUE_SOON_DAYS = 14
REMINDER_EVERY_HOURS = 12


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def interval_months(device: Device, category: DeviceCategory | None) -> int:
    if device.service_interval_months:
        return device.service_interval_months
    if category is not None and category.service_interval_months:
        return category.service_interval_months
    return DEFAULT_INTERVAL_MONTHS


async def category_interval(db, category_slug) -> int:
    """Device.category_id holds the category's slug, not its id."""
    if not category_slug:
        return DEFAULT_INTERVAL_MONTHS
    months = (await db.execute(
        select(DeviceCategory.service_interval_months).where(DeviceCategory.slug == category_slug)
    )).scalar_one_or_none()
    return months or DEFAULT_INTERVAL_MONTHS


def service_state(next_date: date | None, today: date | None = None) -> str:
    """overdue | due_soon | ok | none, for badges and the "Needs you" list."""
    if not next_date:
        return "none"
    today = today or date.today()
    if next_date < today:
        return "overdue"
    if next_date <= today + timedelta(days=DUE_SOON_DAYS):
        return "due_soon"
    return "ok"


async def roll_forward(db, device: Device, log: MaintenanceLog, today: date | None = None) -> None:
    """A maintenance log was just closed: record the service and set the next
    date. The log's own next_due wins when the engineer set one. The device
    goes back to operational when no other log is still open on it and it was
    only "in maintenance" (a reported fault keeps it at fault)."""
    today = today or date.today()
    device.last_maintenance = today
    if log.next_due:
        device.next_maintenance = log.next_due
    else:
        months = device.service_interval_months or await category_interval(db, device.category_id)
        device.next_maintenance = add_months(today, months)
    if device.status == "maintenance":
        still_open = (await db.execute(
            select(func.count(MaintenanceLog.id)).where(
                MaintenanceLog.device_id == device.id,
                MaintenanceLog.id != log.id,
                MaintenanceLog.status != "closed",
            )
        )).scalar_one()
        if not still_open:
            device.status = "operational"


# ── Reminders ────────────────────────────────────────────────

async def _recipients(db, org_ids: set) -> list[tuple[str, str]]:
    """(email, name) of the admins and confirmed responsible engineers of the
    device's clinic organizations."""
    if not org_ids:
        return []
    admins = select(OrgUser.profile_id).where(
        OrgUser.organization_id.in_(org_ids), OrgUser.role == "admin")
    engineers = select(ResponsibleEngineer.engineer_id).where(
        ResponsibleEngineer.organization_id.in_(org_ids),
        ResponsibleEngineer.status == "confirmed")
    rows = (await db.execute(
        select(User.email, Profile.full_name, Profile.username)
        .join(Profile, Profile.id == User.id)
        .where(User.is_active.is_(True), User.id.in_(admins.union(engineers)))
    )).all()
    seen, out = set(), []
    for email, full_name, username in rows:
        if email and email.lower() not in seen:
            seen.add(email.lower())
            out.append((email, full_name or username or ""))
    return out


async def send_due_reminders(db, today: date | None = None) -> dict:
    """Email reminders for devices due soon or overdue that have not had that
    reminder yet for their current due date. Returns counts."""
    from config.email import send_service_reminder_email

    today = today or date.today()
    base = os.getenv("FRONTEND_URL", "http://localhost:8888").rstrip("/")
    devices = (await db.execute(
        select(Device)
        .options(selectinload(Device.healthsite), selectinload(Device.organization))
        .where(
            Device.next_maintenance.is_not(None),
            Device.next_maintenance <= today + timedelta(days=DUE_SOON_DAYS),
            Device.status != "decommissioned",
        )
    )).scalars().all()
    sent = skipped = 0
    for device in devices:
        kind = "overdue" if device.next_maintenance < today else "due_soon"
        already = (await db.execute(
            select(MaintenanceReminder.id).where(
                MaintenanceReminder.device_id == device.id,
                MaintenanceReminder.due_date == device.next_maintenance,
                MaintenanceReminder.kind == kind,
            )
        )).scalar_one_or_none()
        if already:
            skipped += 1
            continue
        org_ids = {i for i in (device.organization_id, device.healthsite_id) if i}
        people = await _recipients(db, org_ids)
        clinic = (device.healthsite or device.organization)
        clinic_name = clinic.name if clinic else ""
        for email, name in people:
            try:
                await send_service_reminder_email(
                    email, name, device.name, device.location or "", clinic_name,
                    device.next_maintenance, kind == "overdue", f"{base}/device/{device.id}",
                )
            except Exception as e:  # one bad address must not stop the rest
                logger.warning("service reminder to %s failed: %s", email, e)
        db.add(MaintenanceReminder(device_id=device.id, due_date=device.next_maintenance,
                                   kind=kind, recipients=len(people)))
        await db.commit()
        sent += 1
    return {"devices_reminded": sent, "already_reminded": skipped}


async def reminder_loop(session_factory) -> None:
    """Runs in the backend process: first pass a minute after start, then
    every REMINDER_EVERY_HOURS. Each due date is emailed once, so restarts
    and several workers at worst repeat the check, not the email (the
    unique constraint on maintenance_reminders backs that up)."""
    await asyncio.sleep(60)
    while True:
        try:
            async with session_factory() as db:
                result = await send_due_reminders(db)
                if result["devices_reminded"]:
                    logger.info("service reminders: %s", result)
        except Exception as e:
            logger.warning("service reminder pass failed: %s", e)
        await asyncio.sleep(REMINDER_EVERY_HOURS * 3600)


def reminders_enabled() -> bool:
    return os.getenv("MAINTENANCE_REMINDERS", "on").strip().lower() not in ("off", "0", "false", "no")
