# routers/onboarding.py — engineer quests, clinic invitations, clinic setup,
# responsible engineers and the talk host's tools. Mounted at /api/onboarding.
#
# Spec: "Engineer and clinic onboarding flow" (2026-11-12). Rules live in
# utils/onboarding.py; this file is the HTTP surface.
#
#   GET  /me                                quests, status, links
#   POST /clinic-invitations                engineer (quests done) invites a clinic
#   GET  /clinic-invitations                the engineer's sent invitations
#   GET  /my-clinics                        clinics that named the engineer
#   GET  /invitations/{token}               public: what an invitation link is
#   POST /invitations/{token}/accept        public: create the account from it
#   POST /invitations/{token}/claim         signed in: attach it to this account
#   GET  /clinic/search?lat&lng | ?q=       healthsites.io facilities near you
#   POST /clinic/pick                       take a healthsites.io facility
#   POST /clinic/create                     a clinic not on healthsites.io yet
#   GET  /clinic/mine                       the clinic account's clinic + setup
#   GET  /clinics/{org}/engineers           Engineers tab (clinic admins)
#   POST /clinics/{org}/engineers           add an engineer by email
#   POST /clinics/{org}/engineers/{id}/confirm | /not-now
#   DELETE /clinics/{org}/engineers/{id}
#   DELETE /clinics/{org}/invitations/{id}
#   GET  /registrable-clinics               Register-device clinic picker
#   GET  /host/applicants, POST /host/applicants/{id}/talk      (talk host)
#   GET  /host/clinics,    POST /host/clinics/{org}/unlock       (talk host)
#
# Every response is built by hand from columns: Profile.user is
# lazy="selectin", so returning ORM rows could leak hashed_password.

import logging
import os
import secrets
import uuid as _uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.users import current_active_user, get_user_manager, UserManager, get_jwt_strategy
from models.models import (
    OnboardingInvitation, Organization, OrgUser, Profile,
    ResponsibleEngineer, User, Device,
)
from utils import onboarding as ob
from utils.profile import get_current_profile
from utils.username import generate_username

router = APIRouter()
logger = logging.getLogger("onboarding")

CLINIC_SEARCH_RADIUS_KM = 5.0
CLINIC_TYPES = ("hospital", "clinic", "health_centre", "lab")


def _frontend_url() -> str:
    from config.users import FRONTEND_URL
    return (FRONTEND_URL or "http://localhost:8888").rstrip("/")


def _links() -> dict:
    return {
        "community_talk_booking": os.getenv("COMMUNITY_BOOKING_URL", ""),
        "clinic_talk_booking": os.getenv("CLINIC_TALK_BOOKING_URL", ""),
    }


def _uuid_or_400(value: str, what: str = "id"):
    try:
        return _uuid.UUID(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {what}")


def _name(p: Profile | None) -> str:
    if p is None:
        return ""
    return p.full_name or p.username or ""


async def _profile(db: AsyncSession, profile_id) -> Profile | None:
    return await db.scalar(select(Profile).where(Profile.id == profile_id))


async def _require_clinic_admin(db: AsyncSession, profile: Profile, org_id) -> Organization:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Clinic not found")
    if profile.get_role_for_org(org_id) != "admin":
        raise HTTPException(status_code=403, detail="Only the clinic's admins can manage its engineers")
    return org


async def _require_talk_host(db: AsyncSession, profile: Profile) -> None:
    if not await ob.can_host_talks(db, profile.user, profile):
        raise HTTPException(status_code=403, detail="Only a talk host can do this")


async def _require_clinic_unlocker(db: AsyncSession, profile: Profile) -> None:
    if not await ob.can_unlock_clinics(db, profile.user, profile):
        raise HTTPException(status_code=403, detail="Only a Clinics Connector can unlock a clinic")


def _org_payload(o: Organization) -> dict:
    return {
        "id": str(o.id),
        "name": o.name,
        "country": o.country,
        "region": o.region,
        "address": o.address,
        "type": o.type,
        "contact_email": o.contact_email,
        "source": o.source,
        "push_to_healthsites": bool(o.push_to_healthsites),
        "clinic_status": o.clinic_status,
        "invited_by": str(o.invited_by) if o.invited_by else None,
    }


# ── Engineer: quests ────────────────────────────────────────────────────────

@router.get("/me")
async def onboarding_me(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Quests, status and what unlocks next. Also promotes an applicant whose
    quests are all done (e.g. right after uploading their picture)."""
    if await ob.refresh_onboarding_status(db, profile):
        await db.commit()
    quests = await ob.quest_state(db, profile)
    superuser = bool(profile.user and profile.user.is_superuser)
    unlocked = ob.is_unlocked(profile, profile.user)
    done = sum(1 for q in quests.values() if q["done"])
    return {
        "member_status": profile.member_status,
        "account_kind": profile.account_kind,
        "is_unlocked": unlocked,
        "is_superuser": superuser,
        "is_talk_host": await ob.is_host(db, profile.user, profile),
        "can_host_talks": await ob.can_host_talks(db, profile.user, profile),
        "can_unlock_clinics": await ob.can_unlock_clinics(db, profile.user, profile),
        "quests": [{"key": k, **quests[k]} for k in ob.QUESTS],
        "quests_done": done,
        "quests_total": len(ob.QUESTS),
        "can_invite_clinics": unlocked and profile.account_kind == "engineer" or superuser,
        "links": _links(),
    }


# ── Engineer: invite a clinic ───────────────────────────────────────────────

class ClinicInviteBody(BaseModel):
    email: EmailStr
    message: Optional[str] = Field(default="", max_length=1000)


@router.post("/clinic-invitations")
async def invite_clinic(
    body: ClinicInviteBody,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if not ob.is_unlocked(profile, profile.user):
        raise HTTPException(status_code=403, detail="quests_pending")
    email = str(body.email).strip().lower()
    inv = OnboardingInvitation(
        kind="clinic",
        email=email,
        message=(body.message or "").strip() or None,
        token=secrets.token_urlsafe(24),
        invited_by=profile.id,
        status="sent",
    )
    db.add(inv)
    await db.commit()

    email_sent = True
    try:
        from config.email import send_clinic_invitation_email
        await send_clinic_invitation_email(
            email, _name(profile), inv.message or "",
            f"{_frontend_url()}/invite/{inv.token}",
        )
    except Exception:
        logger.exception("Failed to send clinic invitation to %s", email)
        email_sent = False
    return {"id": str(inv.id), "email": email, "email_sent": email_sent}


@router.get("/clinic-invitations")
async def my_clinic_invitations(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """The engineer's invitations with where each one is:
    sent → account_created → clinic_ready → confirmed | not_now."""
    rows = (await db.execute(
        select(OnboardingInvitation, Organization)
        .outerjoin(Organization, Organization.id == OnboardingInvitation.organization_id)
        .where(
            OnboardingInvitation.kind == "clinic",
            OnboardingInvitation.invited_by == profile.id,
        )
        .order_by(OnboardingInvitation.created_at.desc())
    )).all()
    org_ids = [org.id for _inv, org in rows if org is not None]
    answers = {}
    if org_ids:
        for re_row in (await db.execute(
            select(ResponsibleEngineer).where(
                ResponsibleEngineer.engineer_id == profile.id,
                ResponsibleEngineer.organization_id.in_(org_ids),
            )
        )).scalars():
            answers[re_row.organization_id] = re_row.status
    out = []
    for inv, org in rows:
        if inv.status == "cancelled":
            status = "cancelled"
        elif inv.status == "sent":
            status = "sent"
        elif org is None:
            status = "account_created"
        else:
            status = {"confirmed": "confirmed", "not_now": "not_now"}.get(answers.get(org.id), "clinic_ready")
        out.append({
            "id": str(inv.id),
            "email": inv.email,
            "message": inv.message,
            "status": status,
            "clinic_id": str(org.id) if org else None,
            "clinic_name": org.name if org else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        })
    return out


@router.get("/my-clinics")
async def my_clinics(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Clinics that named this engineer, with the engineer's state there."""
    rows = (await db.execute(
        select(ResponsibleEngineer, Organization)
        .join(Organization, Organization.id == ResponsibleEngineer.organization_id)
        .where(ResponsibleEngineer.engineer_id == profile.id)
        .order_by(Organization.name)
    )).all()
    return [
        {
            "id": str(org.id),
            "name": org.name,
            "status": await ob.engineer_status(db, row, profile, org.clinic_status),
            "source": row.source,
        }
        for row, org in rows
    ]


# ── Invitation links (public) ───────────────────────────────────────────────

async def _invitation(db: AsyncSession, token: str) -> OnboardingInvitation:
    inv = await db.scalar(select(OnboardingInvitation).where(OnboardingInvitation.token == token))
    if inv is None or inv.status == "cancelled":
        raise HTTPException(status_code=404, detail="invitation_not_found")
    return inv


@router.get("/invitations/{token}")
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)):
    inv = await _invitation(db, token)
    inviter = await _profile(db, inv.invited_by) if inv.invited_by else None
    org = await db.get(Organization, inv.organization_id) if (inv.kind == "engineer" and inv.organization_id) else None
    has_account = bool(await db.scalar(select(User.id).where(func.lower(User.email) == inv.email.lower())))
    return {
        "kind": inv.kind,
        "email": inv.email,
        "message": inv.message,
        "status": inv.status,
        "inviter_name": _name(inviter),
        "clinic_name": org.name if org else None,
        "has_account": has_account,
    }


class AcceptBody(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)


async def _apply_invitation(db: AsyncSession, inv: OnboardingInvitation, profile: Profile) -> None:
    """Attach an invitation to the account that accepted it."""
    inv.status = "accepted"
    inv.accepted_by = profile.id
    inv.accepted_at = ob.now_utc()
    if inv.kind == "engineer" and inv.organization_id:
        existing = await db.scalar(select(ResponsibleEngineer).where(
            ResponsibleEngineer.organization_id == inv.organization_id,
            ResponsibleEngineer.engineer_id == profile.id,
        ))
        if existing is None:
            db.add(ResponsibleEngineer(
                organization_id=inv.organization_id,
                engineer_id=profile.id,
                status="confirmed",
                source="added",
                kind=inv.engineer_kind,
                added_by=inv.invited_by,
                confirmed_by=inv.invited_by,
                confirmed_at=ob.now_utc(),
            ))


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    body: AcceptBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Create the invited account (email from the invitation) and sign it in."""
    from fastapi_users.schemas import BaseUserCreate
    from fastapi_users.exceptions import UserAlreadyExists

    inv = await _invitation(db, token)
    if inv.status != "sent":
        raise HTTPException(status_code=409, detail="invitation_used")
    try:
        user = await user_manager.create(
            BaseUserCreate(email=inv.email, password=body.password), safe=False, request=request,
        )
    except UserAlreadyExists:
        raise HTTPException(status_code=409, detail="user_already_exists")

    # user_manager uses its own session; work on the user through ours.
    user = await db.get(User, user.id)
    user.full_name = body.full_name.strip()
    # The link came by email, so the address is verified.
    user.is_verified = True
    # Network credit for whoever brought this account in.
    user.invited_by = inv.invited_by
    kind = "clinic" if inv.kind == "clinic" else "engineer"
    profile = Profile(
        id=user.id,
        username=await generate_username(body.full_name, db),
        full_name=body.full_name.strip(),
        account_kind=kind,
        # Clinic accounts have no quests (staff); engineers start as applicants.
        member_status="staff" if kind == "clinic" else "applicant",
    )
    db.add(profile)
    await db.flush()
    await _apply_invitation(db, inv, profile)
    await db.commit()

    token_out = await get_jwt_strategy().write_token(user)
    return {"access_token": token_out, "user": {"id": str(user.id), "email": user.email},
            "account_kind": kind}


@router.post("/invitations/{token}/claim")
async def claim_invitation(
    token: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """An invited person who already has an account accepts the invitation
    while signed in."""
    inv = await _invitation(db, token)
    if inv.status != "sent":
        raise HTTPException(status_code=409, detail="invitation_used")
    await _apply_invitation(db, inv, profile)
    await db.commit()
    return {"kind": inv.kind}


# ── Clinic setup ────────────────────────────────────────────────────────────

async def _geocode(q: str) -> tuple[float, float] | None:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(
                "https://nominatim.openstreetmap.org/search",
                params={"format": "jsonv2", "q": q, "limit": 1},
                headers={"User-Agent": "fixmymedtech/1.0 (https://fixmymedtech.com)"},
            )
            resp.raise_for_status()
            data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        logger.warning("Geocoding failed for %r", q)
    return None


@router.get("/clinic/search")
async def clinic_search(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    q: str = "",
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """healthsites.io facilities nearest first, around the browser's location
    or a searched city."""
    from routers.healthsites import find_facilities
    if (lat is None or lng is None) and q.strip():
        point = await _geocode(q.strip())
        if point is None:
            raise HTTPException(status_code=404, detail="place_not_found")
        lat, lng = point
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="lat/lng or q required")
    facilities = await find_facilities(db, lat, lng, CLINIC_SEARCH_RADIUS_KM)
    return {"lat": lat, "lng": lng, "facilities": facilities[:40]}


async def _clinic_invitation_for(db: AsyncSession, profile: Profile) -> OnboardingInvitation | None:
    """The clinic invitation this account accepted and has not used for a
    clinic yet."""
    return await db.scalar(
        select(OnboardingInvitation)
        .where(
            OnboardingInvitation.kind == "clinic",
            OnboardingInvitation.accepted_by == profile.id,
            OnboardingInvitation.organization_id.is_(None),
        )
        .order_by(OnboardingInvitation.accepted_at.desc())
        .limit(1)
    )


async def _finish_clinic(db: AsyncSession, profile: Profile, org: Organization, is_new: bool) -> dict:
    """Make the caller the clinic's admin and record how the clinic arrived:
    invited (the inviting engineer is kept on the clinic, and named with a
    'not now' answer until the clinic confirms them) or not (talk pending)."""
    if not await db.scalar(select(OrgUser.id).where(
        OrgUser.organization_id == org.id, OrgUser.profile_id == profile.id,
    )):
        db.add(OrgUser(profile_id=profile.id, organization_id=org.id, role="admin"))
    else:
        membership = await db.scalar(select(OrgUser).where(
            OrgUser.organization_id == org.id, OrgUser.profile_id == profile.id,
        ))
        membership.role = "admin"

    inv = await _clinic_invitation_for(db, profile)
    invited = inv is not None and inv.invited_by is not None
    if invited:
        inv.organization_id = org.id
        if org.invited_by is None:
            org.invited_by = inv.invited_by
        if not await db.scalar(select(ResponsibleEngineer.id).where(
            ResponsibleEngineer.organization_id == org.id,
            ResponsibleEngineer.engineer_id == inv.invited_by,
        )):
            db.add(ResponsibleEngineer(
                organization_id=org.id,
                engineer_id=inv.invited_by,
                status="not_now",
                source="inviter",
                kind="external",
                added_by=inv.invited_by,
            ))
    else:
        has_devices = await db.scalar(select(Device.id).where(Device.organization_id == org.id).limit(1))
        if is_new or not has_devices:
            org.clinic_status = "talk_pending"
    await db.commit()
    await db.refresh(org)
    return {**_org_payload(org), "invited": invited}


class FacilityBody(BaseModel):
    osm_id: str
    osm_type: str
    name: str
    country: Optional[str] = ""
    region: Optional[str] = ""
    address: Optional[str] = ""
    type: Optional[str] = "clinic"


@router.post("/clinic/pick")
async def clinic_pick(
    body: FacilityBody,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Take a healthsites.io facility as this account's clinic: import it, or
    take over an imported one that has no admin yet."""
    if profile.account_kind != "clinic":
        raise HTTPException(status_code=403, detail="Only clinic accounts set up a clinic here")
    org = await db.scalar(select(Organization).where(
        Organization.osm_id == body.osm_id, Organization.osm_type == body.osm_type,
    ))
    is_new = org is None
    if org is not None:
        if await ob.admin_count(db, org.id) and profile.get_role_for_org(org.id) != "admin":
            raise HTTPException(status_code=409, detail="clinic_has_admin")
    else:
        org_type = body.type if body.type in CLINIC_TYPES else "clinic"
        org = Organization(
            name=body.name.strip(),
            country=(body.country or "").strip(),
            region=(body.region or "").strip(),
            address=(body.address or "").strip(),
            type=org_type,
            osm_id=body.osm_id,
            osm_type=body.osm_type,
            source="healthsites.io",
        )
        db.add(org)
        await db.flush()
    return await _finish_clinic(db, profile, org, is_new)


class ClinicCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country: Optional[str] = ""
    region: Optional[str] = ""
    address: Optional[str] = ""
    type: Optional[str] = "clinic"
    contact_email: Optional[str] = ""


@router.post("/clinic/create")
async def clinic_create(
    body: ClinicCreateBody,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """A clinic that is not on healthsites.io: created here and flagged to be
    pushed to healthsites.io later."""
    if profile.account_kind != "clinic":
        raise HTTPException(status_code=403, detail="Only clinic accounts set up a clinic here")
    org = Organization(
        name=body.name.strip(),
        country=(body.country or "").strip(),
        region=(body.region or "").strip(),
        address=(body.address or "").strip(),
        type=body.type if body.type in CLINIC_TYPES else "clinic",
        contact_email=(body.contact_email or "").strip(),
        source="app",
        push_to_healthsites=True,
    )
    db.add(org)
    await db.flush()
    return await _finish_clinic(db, profile, org, True)


@router.get("/clinic/mine")
async def clinic_mine(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """The clinics this account administers, with what the setup needs next:
    the inviting engineer (to confirm) and the clinic talk."""
    orgs = (await db.execute(
        select(Organization)
        .join(OrgUser, OrgUser.organization_id == Organization.id)
        .where(OrgUser.profile_id == profile.id, OrgUser.role == "admin")
        .order_by(Organization.created_at)
    )).scalars().all()
    out = []
    for org in orgs:
        inviter = await _profile(db, org.invited_by) if org.invited_by else None
        inviter_status = None
        if inviter is not None:
            inviter_status = await db.scalar(select(ResponsibleEngineer.status).where(
                ResponsibleEngineer.organization_id == org.id,
                ResponsibleEngineer.engineer_id == inviter.id,
            ))
        out.append({
            **_org_payload(org),
            "inviter": {"id": str(inviter.id), "name": _name(inviter), "status": inviter_status}
            if inviter else None,
        })
    has_open_invitation = (await _clinic_invitation_for(db, profile)) is not None
    return {"clinics": out, "has_open_invitation": has_open_invitation,
            "account_kind": profile.account_kind, "links": _links()}


# ── Responsible engineers (clinic admins) ───────────────────────────────────

@router.get("/clinics/{org_id}/engineers")
async def clinic_engineers(
    org_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    org_uuid = _uuid_or_400(org_id, "clinic id")
    org = await _require_clinic_admin(db, profile, org_uuid)
    rows = (await db.execute(
        select(ResponsibleEngineer, Profile, User.email)
        .join(Profile, Profile.id == ResponsibleEngineer.engineer_id)
        .join(User, User.id == Profile.id)
        .where(ResponsibleEngineer.organization_id == org_uuid)
        .order_by(ResponsibleEngineer.created_at)
    )).all()
    engineers = []
    for row, eng, email in rows:
        quests = await ob.quest_state(db, eng)
        engineers.append({
            "id": str(eng.id),
            "name": _name(eng),
            "username": eng.username,
            "email": email,
            "status": await ob.engineer_status(db, row, eng, org.clinic_status),
            "answer": row.status,
            "source": row.source,
            "kind": row.kind,
            "is_inviter": org.invited_by == eng.id,
            "quests_done": sum(1 for q in quests.values() if q["done"]) if eng.member_status != "member" else len(ob.QUESTS),
            "quests_total": len(ob.QUESTS),
        })
    invitations = (await db.execute(
        select(OnboardingInvitation).where(
            OnboardingInvitation.kind == "engineer",
            OnboardingInvitation.organization_id == org_uuid,
            OnboardingInvitation.status == "sent",
        ).order_by(OnboardingInvitation.created_at)
    )).scalars().all()
    return {
        "clinic": _org_payload(org),
        "engineers": engineers,
        "invitations": [
            {"id": str(i.id), "email": i.email, "kind": i.engineer_kind,
             "created_at": i.created_at.isoformat() if i.created_at else None}
            for i in invitations
        ],
        "links": _links(),
    }


async def _notify_confirmed(db: AsyncSession, org: Organization, engineer: Profile) -> None:
    email = await db.scalar(select(User.email).where(User.id == engineer.id))
    if not email:
        return
    row = await db.scalar(select(ResponsibleEngineer).where(
        ResponsibleEngineer.organization_id == org.id,
        ResponsibleEngineer.engineer_id == engineer.id,
    ))
    ready = row is not None and (await ob.engineer_status(db, row, engineer, org.clinic_status)) == "can_register"
    try:
        from config.email import send_engineer_confirmed_email
        await send_engineer_confirmed_email(email, _name(engineer), org.name, ready, _frontend_url() + "/getting-started")
    except Exception:
        logger.exception("Failed to send confirmation email to %s", email)


async def _set_answer(db: AsyncSession, profile: Profile, org_id: str, engineer_id: str, status: str):
    org_uuid = _uuid_or_400(org_id, "clinic id")
    eng_uuid = _uuid_or_400(engineer_id, "engineer id")
    org = await _require_clinic_admin(db, profile, org_uuid)
    row = await db.scalar(select(ResponsibleEngineer).where(
        ResponsibleEngineer.organization_id == org_uuid,
        ResponsibleEngineer.engineer_id == eng_uuid,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Engineer not found for this clinic")
    was_confirmed = row.status == "confirmed"
    row.status = status
    if status == "confirmed" and not was_confirmed:
        row.confirmed_by = profile.id
        row.confirmed_at = ob.now_utc()
    await db.commit()
    if status == "confirmed" and not was_confirmed:
        engineer = await _profile(db, eng_uuid)
        if engineer is not None:
            await _notify_confirmed(db, org, engineer)
    return {"status": row.status}


@router.post("/clinics/{org_id}/engineers/{engineer_id}/confirm")
async def confirm_engineer(org_id: str, engineer_id: str,
                           profile: Profile = Depends(get_current_profile),
                           db: AsyncSession = Depends(get_db)):
    return await _set_answer(db, profile, org_id, engineer_id, "confirmed")


@router.post("/clinics/{org_id}/engineers/{engineer_id}/not-now")
async def not_now_engineer(org_id: str, engineer_id: str,
                           profile: Profile = Depends(get_current_profile),
                           db: AsyncSession = Depends(get_db)):
    return await _set_answer(db, profile, org_id, engineer_id, "not_now")


@router.delete("/clinics/{org_id}/engineers/{engineer_id}")
async def remove_engineer(org_id: str, engineer_id: str,
                          profile: Profile = Depends(get_current_profile),
                          db: AsyncSession = Depends(get_db)):
    """Remove a responsible engineer. Devices they registered stay with the
    clinic; the clinic keeps its invited_by whoever is removed."""
    org_uuid = _uuid_or_400(org_id, "clinic id")
    eng_uuid = _uuid_or_400(engineer_id, "engineer id")
    await _require_clinic_admin(db, profile, org_uuid)
    row = await db.scalar(select(ResponsibleEngineer).where(
        ResponsibleEngineer.organization_id == org_uuid,
        ResponsibleEngineer.engineer_id == eng_uuid,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Engineer not found for this clinic")
    await db.delete(row)
    await db.commit()
    return {"removed": 1}


class AddEngineerBody(BaseModel):
    email: EmailStr
    kind: str = "external"


@router.post("/clinics/{org_id}/engineers")
async def add_engineer(
    org_id: str,
    body: AddEngineerBody,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Name an engineer by email. An existing account is confirmed at once and
    told by email; anyone else gets an invitation from the clinic and goes
    through the same three quests."""
    org_uuid = _uuid_or_400(org_id, "clinic id")
    org = await _require_clinic_admin(db, profile, org_uuid)
    kind = body.kind if body.kind in ("internal", "external") else "external"
    email = str(body.email).strip().lower()

    user = await db.scalar(select(User).where(func.lower(User.email) == email))
    if user is not None:
        engineer = await _profile(db, user.id)
        if engineer is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        row = await db.scalar(select(ResponsibleEngineer).where(
            ResponsibleEngineer.organization_id == org_uuid,
            ResponsibleEngineer.engineer_id == engineer.id,
        ))
        if row is not None and row.status == "confirmed":
            raise HTTPException(status_code=409, detail="already_responsible")
        if row is None:
            db.add(ResponsibleEngineer(
                organization_id=org_uuid, engineer_id=engineer.id, status="confirmed",
                source="added", kind=kind, added_by=profile.id,
                confirmed_by=profile.id, confirmed_at=ob.now_utc(),
            ))
        else:
            row.status = "confirmed"
            row.confirmed_by = profile.id
            row.confirmed_at = ob.now_utc()
        await db.commit()
        await _notify_confirmed(db, org, engineer)
        return {"result": "added", "email": email}

    inv = OnboardingInvitation(
        kind="engineer", email=email, token=secrets.token_urlsafe(24),
        invited_by=profile.id, organization_id=org_uuid, engineer_kind=kind, status="sent",
    )
    db.add(inv)
    await db.commit()
    email_sent = True
    try:
        from config.email import send_engineer_invitation_email
        await send_engineer_invitation_email(email, org.name, _name(profile),
                                             f"{_frontend_url()}/invite/{inv.token}")
    except Exception:
        logger.exception("Failed to send engineer invitation to %s", email)
        email_sent = False
    return {"result": "invited", "email": email, "email_sent": email_sent}


@router.delete("/clinics/{org_id}/invitations/{invitation_id}")
async def cancel_engineer_invitation(org_id: str, invitation_id: str,
                                     profile: Profile = Depends(get_current_profile),
                                     db: AsyncSession = Depends(get_db)):
    org_uuid = _uuid_or_400(org_id, "clinic id")
    inv_uuid = _uuid_or_400(invitation_id, "invitation id")
    await _require_clinic_admin(db, profile, org_uuid)
    inv = await db.scalar(select(OnboardingInvitation).where(
        OnboardingInvitation.id == inv_uuid,
        OnboardingInvitation.organization_id == org_uuid,
        OnboardingInvitation.kind == "engineer",
    ))
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.status == "sent":
        inv.status = "cancelled"
        await db.commit()
    return {"status": inv.status}


# ── Device registration ─────────────────────────────────────────────────────

@router.get("/registrable-clinics")
async def get_registrable_clinics(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if await ob.refresh_onboarding_status(db, profile):
        await db.commit()
    return await ob.registrable_clinics(db, profile, profile.user)


# ── Talk host (Community Builders confirm talks, Clinics Connectors unlock clinics) ───────────────────────────────────────────

@router.get("/host/applicants")
async def host_applicants(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    await _require_talk_host(db, profile)
    rows = (await db.execute(
        select(Profile, User.email)
        .join(User, User.id == Profile.id)
        .where(Profile.member_status == "applicant", Profile.account_kind == "engineer")
        .order_by(Profile.created_at.desc())
    )).all()
    out = []
    for p, email in rows:
        quests = await ob.quest_state(db, p)
        out.append({
            "id": str(p.id), "name": _name(p), "username": p.username, "email": email,
            "quests": {k: v["done"] for k, v in quests.items()},
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return out


@router.post("/host/applicants/{profile_id}/talk")
async def host_confirm_talk(
    profile_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    await _require_talk_host(db, profile)
    target = await _profile(db, _uuid_or_400(profile_id, "profile id"))
    if target is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    became_active = await ob.confirm_talk(db, target, profile.id)
    await db.commit()
    return {"confirmed": True, "member_status": target.member_status, "became_active": became_active}


@router.get("/host/clinics")
async def host_clinics(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    await _require_clinic_unlocker(db, profile)
    orgs = (await db.execute(
        select(Organization).where(Organization.clinic_status == "talk_pending")
        .order_by(Organization.created_at.desc())
    )).scalars().all()
    out = []
    for o in orgs:
        admin = (await db.execute(
            select(Profile, User.email)
            .join(OrgUser, OrgUser.profile_id == Profile.id)
            .join(User, User.id == Profile.id)
            .where(OrgUser.organization_id == o.id, OrgUser.role == "admin")
            .limit(1)
        )).first()
        out.append({
            **_org_payload(o),
            "admin_name": _name(admin[0]) if admin else "",
            "admin_email": admin[1] if admin else "",
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return out


@router.post("/host/clinics/{org_id}/unlock")
async def host_unlock_clinic(
    org_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """The clinic talk took place: the clinic may now register devices."""
    await _require_clinic_unlocker(db, profile)
    org = await db.get(Organization, _uuid_or_400(org_id, "clinic id"))
    if org is None:
        raise HTTPException(status_code=404, detail="Clinic not found")
    org.clinic_status = "active"
    org.talk_confirmed_by = profile.id
    org.talk_confirmed_at = ob.now_utc()
    await db.commit()
    return {"clinic_status": org.clinic_status}
