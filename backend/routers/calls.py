# routers/calls.py — "Call an engineer" (wave 4). Rules in utils/calls.py.
#
#   POST /api/calls/{fault_id}/start         clinic: start looking (urgency)
#   POST /api/calls/{fault_id}/cancel        clinic: stop looking
#   GET  /api/calls/{fault_id}               both sides: call, who was told, offers
#   POST /api/calls/{fault_id}/offers        engineer: visit fee + arrival time
#   POST /api/calls/{fault_id}/pass          engineer: not this one
#   POST /api/calls/offers/{id}/accept       clinic
#   POST /api/calls/offers/{id}/counter      clinic, once per offer
#   POST /api/calls/offers/{id}/answer       engineer: take or refuse the counter
#   POST /api/calls/offers/{id}/withdraw     engineer
#   POST /api/calls/{fault_id}/signoff       clinic: it works (rating) or not
#   GET  /api/calls/inbox                    engineer: requests near you
#
# Responses are built from columns (see utils/serialize.py on hashed_password).

import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from models.models import Device, FaultCallNotice, FaultOffer, FaultRating, FaultReport, Profile, User
from utils import calls as cl
from utils import onboarding as ob
from utils.profile import get_current_profile
from utils.serialize import row

router = APIRouter()

BASE = os.getenv("FRONTEND_URL", "http://localhost:8888").rstrip("/")


class CallStart(BaseModel):
    urgency: str = "now"


class OfferIn(BaseModel):
    visit_fee: float = Field(ge=0, le=10_000_000)
    arrival_at: datetime
    note: Optional[str] = Field(default=None, max_length=500)


class CounterIn(BaseModel):
    fee: float = Field(ge=0, le=10_000_000)
    note: Optional[str] = Field(default=None, max_length=500)


class AnswerIn(BaseModel):
    accept: bool


class SignOffIn(BaseModel):
    works: bool
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


# ── loading ───────────────────────────────────────────────────────────────

async def _fault(db, fault_id) -> tuple[FaultReport, Device]:
    fault = await db.get(FaultReport, fault_id)
    if not fault:
        raise HTTPException(status_code=404, detail="Fault report not found")
    device = await db.get(Device, fault.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return fault, device


async def _offer(db, offer_id) -> tuple[FaultOffer, FaultReport, Device]:
    offer = await db.get(FaultOffer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    fault, device = await _fault(db, offer.fault_id)
    return offer, fault, device


async def _notice(db, fault_id, profile_id) -> Optional[FaultCallNotice]:
    return (await db.execute(select(FaultCallNotice).where(
        FaultCallNotice.fault_id == fault_id, FaultCallNotice.engineer_id == profile_id)
    )).scalar_one_or_none()


def _require_decider(profile, device, fault):
    if not cl.can_decide(profile, device, fault):
        raise HTTPException(status_code=403, detail="Only the clinic can do this")


async def _brief(db, ids) -> dict:
    if not ids:
        return {}
    ps = (await db.execute(select(Profile).where(Profile.id.in_(list(ids))))).scalars().all()
    return {p.id: {"id": str(p.id), "full_name": p.full_name, "username": p.username,
                   "avatar_key": p.avatar_key, "city": p.city} for p in ps}


async def _email_people(db, ids):
    return await cl._people(db, ids)


async def _deciders(db, fault, device) -> set:
    """Who hears about offers: the caller/reporter and the clinic admins."""
    from models.models import OrgUser
    ids = {i for i in (fault.call_started_by, fault.reported_by) if i}
    ids |= set((await db.execute(select(OrgUser.profile_id).where(
        OrgUser.organization_id.in_(list(cl.clinic_org_ids(device))), OrgUser.role == "admin"))).scalars().all())
    return ids


def _money(v) -> str:
    if v is None:
        return ""
    n = Decimal(v)
    s = f"{n:,.0f}" if n == n.to_integral() else f"{n:,.2f}"
    return s.replace(",", " ")


# ── state ─────────────────────────────────────────────────────────────────

async def _state(db, fault: FaultReport, device: Device, profile: Profile) -> dict:
    offers = (await db.execute(select(FaultOffer).where(FaultOffer.fault_id == fault.id)
                               .order_by(FaultOffer.created_at))).scalars().all()
    notices = (await db.execute(select(FaultCallNotice).where(FaultCallNotice.fault_id == fault.id)
                                .order_by(FaultCallNotice.notified_at))).scalars().all()
    decider = cl.can_decide(profile, device, fault)
    my_notice = next((n for n in notices if n.engineer_id == profile.id), None)
    if not decider and my_notice is None and fault.assigned_to != profile.id and not cl.is_superuser(profile):
        raise HTTPException(status_code=403, detail="This request is not open to you")
    people = await _brief(db, {o.engineer_id for o in offers} | {n.engineer_id for n in notices})
    ratings = await cl.ratings_for(db, {o.engineer_id for o in offers})
    rating = (await db.execute(select(FaultRating).where(FaultRating.fault_id == fault.id))).scalar_one_or_none()

    def offer_out(o: FaultOffer) -> dict:
        avg, n = ratings.get(o.engineer_id, (None, 0))
        d = row(o)
        d.update(engineer=people.get(o.engineer_id), rating_avg=avg, rating_count=n,
                 fee_label=_money(o.visit_fee), counter_label=_money(o.counter_fee),
                 agreed_label=_money(o.agreed_fee), mine=o.engineer_id == profile.id)
        return d

    visible = offers if decider else [o for o in offers if o.engineer_id == profile.id]
    tiers = {}
    for n in notices:
        tiers[n.tier] = tiers.get(n.tier, 0) + 1
    my_offer = next((o for o in offers if o.engineer_id == profile.id), None)
    return {
        "fault": {k: v for k, v in row(fault).items()
                  if k in ("id", "device_id", "description", "severity", "status", "reported_at",
                           "call_status", "urgency", "call_started_at", "call_widened_at",
                           "assigned_to", "diagnosis", "quote_amount", "final_price", "resolved_at",
                           "resolution_notes", "photo_key")},
        "device": {"id": str(device.id), "name": device.name, "location": device.location,
                   "manufacturer": device.manufacturer, "model": device.model,
                   "status": device.status},
        "told": {"total": len(notices), "by_tier": tiers,
                 # Names are for the clinic; engineers only see counts.
                 "names": [people.get(n.engineer_id, {}).get("full_name") or people.get(n.engineer_id, {}).get("username")
                           for n in notices if n.passed_at is None] if decider else []},
        "offers": [offer_out(o) for o in visible],
        "rating": row(rating) if rating else None,
        "assignee": (await _brief(db, {fault.assigned_to})).get(fault.assigned_to) if fault.assigned_to else None,
        "viewer": {
            "is_decider": decider,
            "can_offer": bool(fault.call_status == "searching" and my_notice and my_notice.passed_at is None
                              and my_offer is None and ob.is_unlocked(profile, profile.user)),
            "passed": bool(my_notice and my_notice.passed_at),
            "my_offer_id": str(my_offer.id) if my_offer else None,
            "is_assignee": fault.assigned_to == profile.id,
            "can_counter": cl.MAX_COUNTERS > 0,
        },
        "currency": cl.CURRENCY,
    }


# ── clinic side ───────────────────────────────────────────────────────────

@router.post("/{fault_id}/start")
async def start(fault_id: UUID, body: CallStart, profile: Profile = Depends(get_current_profile),
                db: AsyncSession = Depends(get_db)):
    fault, device = await _fault(db, fault_id)
    if not cl.can_call(profile, device):
        raise HTTPException(status_code=403, detail="Only the clinic's people can call an engineer")
    if body.urgency not in ("now", "this_week"):
        raise HTTPException(status_code=400, detail="Urgency must be now or this_week")
    if fault.status != "open" or fault.assigned_to:
        raise HTTPException(status_code=409, detail="This fault already has an engineer")
    if fault.call_status == "searching":
        raise HTTPException(status_code=409, detail="Already looking for an engineer")
    told = await cl.start_call(db, fault, device, profile, body.urgency)
    await db.commit()
    return {"told": told, "call_status": fault.call_status}


@router.post("/{fault_id}/cancel")
async def cancel(fault_id: UUID, profile: Profile = Depends(get_current_profile),
                 db: AsyncSession = Depends(get_db)):
    fault, device = await _fault(db, fault_id)
    _require_decider(profile, device, fault)
    if fault.call_status != "searching":
        raise HTTPException(status_code=409, detail="Not looking for an engineer")
    fault.call_status = "closed"
    offers = (await db.execute(select(FaultOffer).where(FaultOffer.fault_id == fault.id))).scalars().all()
    cl.lapse_others(offers, None)
    await db.commit()
    return {"call_status": "closed"}


@router.get("/inbox")
async def inbox(profile: Profile = Depends(get_current_profile), db: AsyncSession = Depends(get_db)):
    """Requests this engineer was told about and has not passed on, newest
    first, plus everything they have offered on that is still in play."""
    notices = (await db.execute(
        select(FaultCallNotice, FaultReport, Device)
        .join(FaultReport, FaultReport.id == FaultCallNotice.fault_id)
        .join(Device, Device.id == FaultReport.device_id)
        .where(FaultCallNotice.engineer_id == profile.id)
        .order_by(FaultReport.call_started_at.desc())
        .limit(100)
    )).all()
    offers = {o.fault_id: o for o in (await db.execute(
        select(FaultOffer).where(FaultOffer.engineer_id == profile.id))).scalars().all()}
    open_, mine = [], []
    for n, f, d in notices:
        item = {
            "fault_id": str(f.id), "device_name": d.name, "location": d.location,
            "description": f.description, "urgency": f.urgency, "call_status": f.call_status,
            "status": f.status, "called_at": f.call_started_at, "tier": n.tier,
        }
        o = offers.get(f.id)
        if o is not None:
            item.update(offer_status=o.status, fee_label=_money(o.agreed_fee or o.visit_fee),
                        counter_label=_money(o.counter_fee), arrival_at=o.arrival_at)
            if o.status in ("pending", "countered") or (o.status == "accepted" and f.status != "resolved"):
                mine.append(item)
        elif f.call_status == "searching" and n.passed_at is None:
            open_.append(item)
    return {"open": open_, "mine": mine, "currency": cl.CURRENCY,
            "can_offer": ob.is_unlocked(profile, profile.user)}


@router.get("/{fault_id}")
async def get_call(fault_id: UUID, profile: Profile = Depends(get_current_profile),
                   db: AsyncSession = Depends(get_db)):
    fault, device = await _fault(db, fault_id)
    return await _state(db, fault, device, profile)


# ── engineer side ─────────────────────────────────────────────────────────

@router.post("/{fault_id}/offers")
async def make_offer(fault_id: UUID, body: OfferIn, profile: Profile = Depends(get_current_profile),
                     db: AsyncSession = Depends(get_db)):
    from config.email import send_offer_email
    fault, device = await _fault(db, fault_id)
    if fault.call_status != "searching":
        raise HTTPException(status_code=409, detail="This request is no longer open")
    notice = await _notice(db, fault.id, profile.id)
    if notice is None or notice.passed_at is not None:
        raise HTTPException(status_code=403, detail="This request is not open to you")
    if not ob.is_unlocked(profile, profile.user):
        raise HTTPException(status_code=403, detail="Finish your welcome steps to make offers")
    if await db.scalar(select(FaultOffer.id).where(FaultOffer.fault_id == fault.id,
                                                   FaultOffer.engineer_id == profile.id)):
        raise HTTPException(status_code=409, detail="You already made an offer")
    arrival = body.arrival_at if body.arrival_at.tzinfo else body.arrival_at.replace(tzinfo=cl.now().tzinfo)
    if arrival < cl.now() - timedelta(minutes=15) or arrival > cl.now() + timedelta(days=14):
        raise HTTPException(status_code=400, detail="Arrival must be within the next two weeks")
    offer = FaultOffer(fault_id=fault.id, engineer_id=profile.id, visit_fee=Decimal(str(body.visit_fee)),
                       currency=cl.CURRENCY, arrival_at=arrival, note=(body.note or "").strip() or None)
    db.add(offer)
    await db.commit()
    who = profile.full_name or profile.username
    for _pid, email, full_name, username in await _email_people(db, await _deciders(db, fault, device)):
        try:
            await send_offer_email(email, full_name or username or "", who, device.name,
                                   f"{_money(offer.visit_fee)} {cl.CURRENCY}",
                                   arrival.strftime("%d %b %H:%M UTC"), f"{BASE}/calls/{fault.id}")
        except Exception:
            pass
    return {"id": str(offer.id), "status": offer.status}


@router.post("/{fault_id}/pass")
async def pass_call(fault_id: UUID, profile: Profile = Depends(get_current_profile),
                    db: AsyncSession = Depends(get_db)):
    notice = await _notice(db, fault_id, profile.id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Not in your requests")
    notice.passed_at = cl.now()
    await db.commit()
    return {"passed": True}


@router.post("/offers/{offer_id}/withdraw")
async def withdraw(offer_id: UUID, profile: Profile = Depends(get_current_profile),
                   db: AsyncSession = Depends(get_db)):
    offer, fault, device = await _offer(db, offer_id)
    if offer.engineer_id != profile.id:
        raise HTTPException(status_code=403, detail="Not your offer")
    if offer.status not in ("pending", "countered"):
        raise HTTPException(status_code=409, detail="This offer is already decided")
    offer.status = "withdrawn"
    await db.commit()
    return {"status": offer.status}


async def _agree(db, offer: FaultOffer, fault: FaultReport, device: Device, by: UUID, fee):
    if fault.status not in ("open", "assigned") or fault.call_status != "searching":
        raise HTTPException(status_code=409, detail="This request is no longer open")
    offers = (await db.execute(select(FaultOffer).where(FaultOffer.fault_id == fault.id))).scalars().all()
    offer.status = "accepted"
    offer.agreed_fee = fee
    offer.decided_by = by
    offer.decided_at = cl.now()
    cl.lapse_others(offers, offer.id)
    # Today's "assign" step, performed by the agreement.
    fault.assigned_to = offer.engineer_id
    fault.assigned_by = by
    fault.assigned_at = cl.now()
    fault.status = "assigned"
    fault.call_status = "agreed"


@router.post("/offers/{offer_id}/accept")
async def accept(offer_id: UUID, profile: Profile = Depends(get_current_profile),
                 db: AsyncSession = Depends(get_db)):
    from config.email import send_offer_update_email
    offer, fault, device = await _offer(db, offer_id)
    _require_decider(profile, device, fault)
    if offer.status != "pending":
        raise HTTPException(status_code=409, detail="Only a pending offer can be accepted")
    await _agree(db, offer, fault, device, profile.id, offer.visit_fee)
    await db.commit()
    for _pid, email, full_name, username in await _email_people(db, {offer.engineer_id}):
        try:
            await send_offer_update_email(
                email, full_name or username or "", device.name, "Your offer was accepted",
                f"The clinic accepted your visit for {device.name}: {_money(offer.agreed_fee)} {offer.currency}, "
                f"{offer.arrival_at.strftime('%d %b %H:%M UTC')}.", f"{BASE}/requests/{fault.id}")
        except Exception:
            pass
    return {"status": offer.status}


@router.post("/offers/{offer_id}/counter")
async def counter(offer_id: UUID, body: CounterIn, profile: Profile = Depends(get_current_profile),
                  db: AsyncSession = Depends(get_db)):
    from config.email import send_offer_update_email
    offer, fault, device = await _offer(db, offer_id)
    _require_decider(profile, device, fault)
    if cl.MAX_COUNTERS < 1 or offer.countered_at is not None:
        raise HTTPException(status_code=409, detail="You can ask for a lower fee only once")
    if offer.status != "pending" or fault.call_status != "searching":
        raise HTTPException(status_code=409, detail="Only a pending offer can be countered")
    offer.counter_fee = Decimal(str(body.fee))
    offer.counter_note = (body.note or "").strip() or None
    offer.countered_by = profile.id
    offer.countered_at = cl.now()
    offer.status = "countered"
    await db.commit()
    for _pid, email, full_name, username in await _email_people(db, {offer.engineer_id}):
        try:
            await send_offer_update_email(
                email, full_name or username or "", device.name, "The clinic asks for a lower fee",
                f"For {device.name} the clinic asks {_money(offer.counter_fee)} {offer.currency} instead of "
                f"{_money(offer.visit_fee)}. Accept or decline.", f"{BASE}/requests/{fault.id}")
        except Exception:
            pass
    return {"status": offer.status}


@router.post("/offers/{offer_id}/answer")
async def answer(offer_id: UUID, body: AnswerIn, profile: Profile = Depends(get_current_profile),
                 db: AsyncSession = Depends(get_db)):
    offer, fault, device = await _offer(db, offer_id)
    if offer.engineer_id != profile.id:
        raise HTTPException(status_code=403, detail="Not your offer")
    if offer.status != "countered":
        raise HTTPException(status_code=409, detail="There is no counter-offer to answer")
    if body.accept:
        await _agree(db, offer, fault, device, offer.countered_by or profile.id, offer.counter_fee)
    else:
        offer.status = "declined"
        offer.decided_by = profile.id
        offer.decided_at = cl.now()
    await db.commit()
    return {"status": offer.status}


# ── sign-off ──────────────────────────────────────────────────────────────

@router.post("/{fault_id}/signoff")
async def sign_off(fault_id: UUID, body: SignOffIn, profile: Profile = Depends(get_current_profile),
                   db: AsyncSession = Depends(get_db)):
    from config.email import send_offer_update_email
    fault, device = await _fault(db, fault_id)
    _require_decider(profile, device, fault)
    if fault.status != "resolved":
        raise HTTPException(status_code=409, detail="The repair is not marked as done yet")
    if await db.scalar(select(FaultRating.id).where(FaultRating.fault_id == fault.id)):
        raise HTTPException(status_code=409, detail="Already signed off")
    if body.works:
        if not body.rating:
            raise HTTPException(status_code=400, detail="Give the repair 1 to 5 stars")
        db.add(FaultRating(fault_id=fault.id, engineer_id=fault.assigned_to, rated_by=profile.id,
                           rating=body.rating, comment=(body.comment or "").strip() or None))
        if fault.call_status:
            fault.call_status = "closed"
        await db.commit()
        return {"signed_off": True}
    # Not working: back to the engineer, same agreement.
    fault.status = "in_progress"
    fault.resolved_at = None
    if device.status == "operational" and fault.severity in ("high", "critical"):
        device.status = "fault"
    await db.commit()
    if fault.assigned_to:
        for _pid, email, full_name, username in await _email_people(db, {fault.assigned_to}):
            try:
                await send_offer_update_email(
                    email, full_name or username or "", device.name, "The clinic says it still doesn't work",
                    f"{device.name} is not working yet. Note from the clinic: {(body.comment or '').strip() or '-'}",
                    f"{BASE}/device/{device.id}/fault/{fault.id}")
            except Exception:
                pass
    return {"signed_off": False, "status": fault.status}
