# utils/calls.py — "Call an engineer" (wave 4, migration 032).
#
# Matching order (fault_call_notices.tier):
#   1. responsible  the clinic's confirmed responsible engineers, and the
#                   technicians/engineers of the device's maintenance org
#   2. registrant   the engineer who registered the device (proposal)
#   3. city         Contributors whose profile city matches the clinic's,
#                   told once the call "widens": at once when tiers 1-2 are
#                   empty, else after WIDEN_MINUTES without an offer.
# Only engineers who were told can make an offer (one each). OFFER_POOL
# narrows or widens tier 3; it is the open "who can make offers?" question,
# kept as one setting so the answer is a one-line change:
#   city (default) · own (tiers 1-2 only) · country (Contributors in the
#   clinic's country).
#
# An offer is a visit fee and an arrival time (it covers coming and
# diagnosing; the repair is priced later by the existing diagnosis quote).
# The clinic may counter an offer once; the engineer then accepts or
# declines. Accepting performs the fault workflow's "assign" step.
# No payment is handled: fees are recorded only.

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from models.models import (
    Device, FaultCallNotice, FaultOffer, FaultRating, FaultReport, Organization,
    OrgUser, Profile, ResponsibleEngineer, User,
)

logger = logging.getLogger("calls")

OFFER_POOL = os.getenv("CALL_OFFER_POOL", "city").strip().lower()
WIDEN_MINUTES = {"now": 20, "this_week": 240}
CURRENCY = os.getenv("CALL_CURRENCY", "XAF").strip() or "XAF"
MAX_COUNTERS = 1          # proposal: one counter-offer, then agree or not
ENGINEER_ROLES = ("technician", "engineering_staff")
LOOP_EVERY_SECONDS = 300


def now() -> datetime:
    return datetime.now(timezone.utc)


def clinic_org_ids(device: Device) -> set:
    return {i for i in (device.organization_id, device.healthsite_id) if i}


def decider_org_ids(device: Device) -> set:
    return clinic_org_ids(device) | ({device.organization_maintenance_id} if device.organization_maintenance_id else set())


def is_superuser(profile: Profile) -> bool:
    return bool(profile.user and profile.user.is_superuser)


def can_call(profile: Profile, device: Device) -> bool:
    """Anyone with a role at the device's clinic (or its maintenance org)."""
    return is_superuser(profile) or bool(set(profile.org_ids()) & decider_org_ids(device))


def can_decide(profile: Profile, device: Device, fault: FaultReport) -> bool:
    """Accept, counter, cancel and sign off: whoever called or reported it,
    the admins of the clinic and of the maintenance org, superusers."""
    if is_superuser(profile):
        return True
    if profile.id in (fault.call_started_by, fault.reported_by):
        return True
    return any(profile.get_role_for_org(o) == "admin" for o in decider_org_ids(device))


def _city_match(city: str | None, org: Organization | None) -> bool:
    if not city or org is None:
        return False
    c = city.strip().lower()
    hay = " ".join(x for x in (org.region, org.address, org.name) if x).lower()
    return bool(c) and c in hay


async def candidates(db, device: Device, exclude: set) -> dict:
    """{profile_id: tier} for everyone this call may reach, best tier first."""
    out: dict = {}
    clinics = clinic_org_ids(device)

    # Tier 1: the clinic's own engineers.
    rows = (await db.execute(
        select(ResponsibleEngineer.engineer_id)
        .join(Profile, Profile.id == ResponsibleEngineer.engineer_id)
        .where(ResponsibleEngineer.organization_id.in_(clinics),
               ResponsibleEngineer.status == "confirmed",
               Profile.member_status == "member")
    )).scalars().all() if clinics else []
    staff = (await db.execute(
        select(OrgUser.profile_id).where(
            OrgUser.organization_id == device.organization_maintenance_id,
            OrgUser.role.in_(ENGINEER_ROLES))
    )).scalars().all() if device.organization_maintenance_id else []
    for pid in [*rows, *staff]:
        out.setdefault(pid, "responsible")

    # Tier 2: the registrant (proposal: the registrant is called early).
    if device.registered_by:
        reg = await db.get(Profile, device.registered_by)
        if reg is not None and reg.member_status == "member":
            out.setdefault(reg.id, "registrant")

    # Tier 3: Contributors near the clinic.
    if OFFER_POOL in ("city", "country"):
        clinic = None
        for oid in (device.healthsite_id, device.organization_id):
            if oid:
                clinic = await db.get(Organization, oid)
                if clinic:
                    break
        if clinic is not None:
            q = select(Profile).where(Profile.member_status == "member",
                                      Profile.account_kind == "engineer")
            if clinic.country:
                q = q.where(func.lower(Profile.country) == clinic.country.strip().lower())
            for p in (await db.execute(q)).scalars().all():
                if OFFER_POOL == "country" or _city_match(p.city, clinic):
                    out.setdefault(p.id, "city")

    for pid in exclude:
        out.pop(pid, None)
    return out


async def _people(db, ids) -> list[tuple]:
    if not ids:
        return []
    return (await db.execute(
        select(Profile.id, User.email, Profile.full_name, Profile.username)
        .join(User, User.id == Profile.id)
        .where(Profile.id.in_(list(ids)), User.is_active.is_(True))
    )).all()


async def notify(db, fault: FaultReport, device: Device, tiers: tuple) -> int:
    """Tell the engineers of the given tiers who have not been told yet."""
    from config.email import send_call_email
    exclude = {i for i in (fault.call_started_by, fault.reported_by) if i}
    cands = await candidates(db, device, exclude)
    told = set((await db.execute(
        select(FaultCallNotice.engineer_id).where(FaultCallNotice.fault_id == fault.id)
    )).scalars().all())
    new = {pid: tier for pid, tier in cands.items() if tier in tiers and pid not in told}
    for pid, tier in new.items():
        db.add(FaultCallNotice(fault_id=fault.id, engineer_id=pid, tier=tier))
    await db.flush()
    base = os.getenv("FRONTEND_URL", "http://localhost:8888").rstrip("/")
    for pid, email, full_name, username in await _people(db, new.keys()):
        try:
            await send_call_email(email, full_name or username or "", device.name,
                                  device.location or "", fault.urgency or "this_week",
                                  f"{base}/requests/{fault.id}")
        except Exception as e:
            logger.warning("call email to %s failed: %s", email, e)
    return len(new)


async def start_call(db, fault: FaultReport, device: Device, profile: Profile, urgency: str) -> int:
    fault.call_status = "searching"
    fault.urgency = urgency
    fault.call_started_at = now()
    fault.call_started_by = profile.id
    n = await notify(db, fault, device, ("responsible", "registrant"))
    if n == 0:
        fault.call_widened_at = now()
        n = await notify(db, fault, device, ("city",))
    return n


async def widen_due(db) -> int:
    """Calls still searching with no offer after WIDEN_MINUTES reach tier 3."""
    widened = 0
    faults = (await db.execute(
        select(FaultReport).options(selectinload(FaultReport.device))
        .where(FaultReport.call_status == "searching", FaultReport.call_widened_at.is_(None))
    )).scalars().all()
    for f in faults:
        minutes = WIDEN_MINUTES.get(f.urgency or "this_week", 240)
        if f.call_started_at and f.call_started_at > now() - timedelta(minutes=minutes):
            continue
        offers = await db.scalar(select(func.count(FaultOffer.id)).where(
            FaultOffer.fault_id == f.id, FaultOffer.status.in_(("pending", "countered"))))
        if offers:
            continue
        f.call_widened_at = now()
        await notify(db, f, f.device, ("city",))
        await db.commit()
        widened += 1
    return widened


async def call_loop(session_factory) -> None:
    await asyncio.sleep(30)
    while True:
        try:
            async with session_factory() as db:
                await widen_due(db)
        except Exception as e:
            logger.warning("call widening pass failed: %s", e)
        await asyncio.sleep(LOOP_EVERY_SECONDS)


async def ratings_for(db, ids) -> dict:
    """{engineer_id: (average, count)}"""
    if not ids:
        return {}
    rows = (await db.execute(
        select(FaultRating.engineer_id, func.avg(FaultRating.rating), func.count(FaultRating.id))
        .where(FaultRating.engineer_id.in_(list(ids)))
        .group_by(FaultRating.engineer_id)
    )).all()
    return {eid: (round(float(avg), 1), int(n)) for eid, avg, n in rows}


def lapse_others(offers, keep_id) -> None:
    for o in offers:
        if o.id != keep_id and o.status in ("pending", "countered"):
            o.status = "lapsed"
