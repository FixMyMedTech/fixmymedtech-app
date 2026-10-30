# routers/community.py — community journey API, mounted at /api/community
#
# Plan: docs/docs/community-journey.md. Engine: utils/community.py.
#
#   Public
#     GET  /tree                     the skill tree (roles, requirements, permissions)
#     GET  /config                   booking link and intro video URLs
#     POST /join                     create an account (a community applicant) → {access_token}
#     GET  /public/stats             members per country (for fixmymedtech.org)
#   Signed in (any status, so applicants can do their quests)
#     GET  /me                       status, welcome quests, roles, progress, permissions
#     POST /me/quests/intro_video    the intro video was watched
#     POST /me/consent               {social: true|false}
#     PATCH /me/story                city, country, country trained in, why biomedical engineering
#     POST /me/claim/{role_key}      take a `claim` role whose requirements are met
#   Community dashboard (each route names the permission it needs)
#     GET   /admin/applicants                       view_applicants
#     GET   /admin/applicants/{id}                  view_applicants
#     PATCH /admin/applicants/{id}                  decide_applicants   host, meeting time, notes
#     POST  /admin/applicants/{id}/meeting-held     decide_applicants   completes the meeting quest
#     POST  /admin/applicants/{id}/quests/{key}     confirm_quests      e.g. discord_joined without Discord login
#     POST  /admin/applicants/{id}/refuse           decide_applicants
#     POST  /admin/applicants/{id}/reopen           decide_applicants
#     GET   /admin/hosts                            view_applicants     who can host a welcome meeting
#     GET   /admin/members                          view_members
#     GET   /admin/members/{id}                     view_members
#     POST  /admin/members/{id}/roles               assign_roles
#     DELETE /admin/member-roles/{id}?reason=       assign_roles
#     GET   /admin/permissions                      any dashboard permission
#     GET   /admin/history                          view_role_history
#
# Every response is built by hand from columns. Never return ORM rows:
# Profile.user is selectin-loaded and would leak hashed_password.

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.users import current_active_user, get_user_manager, UserManager, get_jwt_strategy
from models.models import (
    User, Profile, Organization, OrgUser, CommunityRole, MemberRole, MemberQuest,
    CommunityApplication, CommunityRoleChange, CommunityRolePermission,
)
from utils import community as cm
from utils.username import generate_username

router = APIRouter()

KINDS = ("engineer", "student", "clinician", "other")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _config() -> dict:
    main_video = os.getenv("COMMUNITY_INTRO_VIDEO_URL", "").strip()
    return {
        "booking_url": os.getenv("COMMUNITY_BOOKING_URL", "").strip(),
        "intro_video_url": main_video,
        "staff_intro_video_url": os.getenv("STAFF_INTRO_VIDEO_URL", "").strip() or main_video,
        "discord_invite_url": os.getenv("DISCORD_INVITE_URL", "").strip(),
    }


def _role_out(role: dict) -> dict:
    return {k: role[k] for k in ("key", "path", "tier", "scope", "unlock", "sort", "names",
                                 "descriptions", "linkedin_titles", "requirements", "permissions")}


def _holding_out(h: MemberRole, roles_by_key: dict, paused: bool) -> dict:
    role = roles_by_key.get(h.role_key, {})
    return {
        "id": str(h.id),
        "role_key": h.role_key,
        "names": role.get("names", {}),
        "linkedin_titles": role.get("linkedin_titles", {}),
        "path": role.get("path"),
        "tier": role.get("tier"),
        "country": h.country,
        "team": h.team,
        "status": h.status,
        "paused": paused,
        "source": h.source,
        "granted_at": _iso(h.granted_at),
        "removed_at": _iso(h.removed_at),
        "removed_reason": h.removed_reason,
    }


async def _welcome_quests(profile: Profile, quests: dict) -> list[dict]:
    checked_by = {
        "profile_complete": "auto", "intro_video": "auto", "meeting_held": "host",
        "discord_joined": "auto", "consent_answered": "auto",
    }
    return [{"key": q, "done": quests.get(q, 0) >= 1, "checked": checked_by[q]} for q in cm.WELCOME_QUESTS]


# ── Public ───────────────────────────────────────────────────

@router.get("/tree")
async def tree(db: AsyncSession = Depends(get_db)):
    catalogue = await cm.load_catalogue(db)
    holders = dict((await db.execute(
        select(MemberRole.role_key, func.count())
        .where(MemberRole.status == "active")
        .group_by(MemberRole.role_key)
    )).all())
    return {
        "roles": [{**_role_out(r), "holders": int(holders.get(r["key"], 0))} for r in catalogue],
        "paths": ["start", "devices", "people", "trust", "knowledge", "teams", "parts", "leads"],
        "teams": list(cm.TEAMS),
        "permissions": {k: {"group": v["group"], "en": v["en"]} for k, v in cm.PERMISSIONS.items()},
    }


@router.get("/config")
async def config():
    return _config()


class JoinRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8)
    country: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    kind: str = "other"
    organisation: Optional[str] = Field(default=None, max_length=200)
    country_trained: Optional[str] = Field(default=None, max_length=100)
    motivation: Optional[str] = Field(default=None, max_length=1000)
    heard_from: Optional[str] = Field(default=None, max_length=200)
    ref: Optional[str] = Field(default=None, max_length=100)


@router.post("/join")
async def join(
    body: JoinRequest,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
    db: AsyncSession = Depends(get_db),
):
    """The one way into the community. Creates the account straight away, as
    a community applicant who can only use the start page until the welcome
    quests are done. Returns a token so the person is signed in at once."""
    from fastapi_users.schemas import BaseUserCreate
    from fastapi_users.exceptions import UserAlreadyExists

    if body.kind not in KINDS:
        raise HTTPException(status_code=400, detail="invalid_kind")
    email = str(body.email).strip().lower()

    # Referral: /join?ref=<username> credits the member who shared the link.
    referrer = None
    if body.ref:
        referrer = await db.scalar(select(Profile.id).where(Profile.username == body.ref.strip()))

    try:
        user = await user_manager.create(BaseUserCreate(email=email, password=body.password),
                                         safe=False, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=409, detail="user_already_exists")

    user = await db.get(User, user.id)
    user.full_name = body.full_name.strip()
    if referrer:
        user.invited_by = referrer

    profile = Profile(
        id=user.id,
        username=await generate_username(body.full_name, db),
        full_name=body.full_name.strip(),
        country=body.country.strip(),
        city=body.city.strip(),
        country_trained=(body.country_trained or "").strip() or None,
        member_status="applicant",
        join_path="community",
    )
    db.add(profile)
    await db.flush()

    # Every account has a personal organization, as with /signup, so the
    # platform works the day the quests are done.
    org = Organization(name=body.full_name.strip(), country=body.country.strip(), type="hospital")
    db.add(org)
    await db.flush()
    db.add(OrgUser(profile_id=user.id, organization_id=org.id, role="admin"))

    db.add(CommunityApplication(
        profile_id=user.id, kind=body.kind,
        organisation=(body.organisation or "").strip() or None,
        motivation=(body.motivation or "").strip() or None,
        heard_from=(body.heard_from or "").strip() or None,
        status="open",
    ))
    await cm.log_change(db, user.id, "applicant_joined", str(user.id),
                        after={"kind": body.kind, "country": profile.country, "city": profile.city})
    await db.commit()

    token = await get_jwt_strategy().write_token(user)
    return {"access_token": token, "user": {"id": str(user.id), "email": user.email}}


@router.get("/public/stats")
async def public_stats(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Profile.country, func.count())
        .where(Profile.member_status == "member")
        .group_by(Profile.country)
    )).all()
    per_country = {(c or ""): int(n) for c, n in rows}
    return {
        "members": sum(per_country.values()),
        "countries": len([c for c in per_country if c]),
        "members_per_country": {c: n for c, n in per_country.items() if c},
    }


# ── Me ───────────────────────────────────────────────────────

async def _me_payload(db: AsyncSession, profile: Profile, user: User) -> dict:
    catalogue = await cm.load_catalogue(db)
    roles_by_key = {r["key"]: r for r in catalogue}
    prog = await cm.progress(db, profile, user, catalogue)
    scopes = await cm.permission_scopes(db, profile, user)
    app = await db.get(CommunityApplication, profile.id)
    host_name = None
    if app and app.host_id:
        host_name = await db.scalar(select(Profile.full_name).where(Profile.id == app.host_id))

    # Next unlocks: roles not held whose requirements are partly met, closest first.
    candidates = []
    for role in catalogue:
        state = prog["per_role"][role["key"]]
        if state["held"] or role["unlock"] == "assigned" or role["key"] == "ambassador":
            continue
        prereq_ok = all(r["met"] for r in state["requirements"] if r["kind"] == "role")
        if not prereq_ok:
            continue
        candidates.append({
            "key": role["key"], "names": role["names"], "unlock": role["unlock"],
            "met": state["met"], "total": state["total"], "ready": state["ready"],
            "requirements": state["requirements"],
        })
    candidates.sort(key=lambda c: (-(c["met"] / c["total"] if c["total"] else 0), roles_by_key[c["key"]]["tier"]))

    return {
        "id": str(profile.id),
        "full_name": profile.full_name,
        "member_status": profile.member_status,
        "join_path": profile.join_path,
        "member_since": _iso(profile.member_since),
        "is_superuser": bool(user.is_superuser),
        "story": {
            "country": profile.country, "city": profile.city,
            "country_trained": profile.country_trained, "why_bme": profile.why_bme,
            "has_photo": bool(profile.avatar_key),
        },
        "social_consent": profile.social_consent,
        "discord_linked": bool(user.discord_user_id),
        "welcome_quests": await _welcome_quests(profile, prog["quests"]),
        "application": {
            "status": app.status, "kind": app.kind,
            "meeting_at": _iso(app.meeting_at), "meeting_held_at": _iso(app.meeting_held_at),
            "host_name": host_name,
            "decision_reason": app.decision_reason if app.status == "refused" else None,
        } if app else None,
        "roles": [_holding_out(h, roles_by_key, prog["paused"]) for h in prog["roles"]],
        "paused": prog["paused"],
        "metrics": prog["metrics"],
        "progress": {k: {"met": v["met"], "total": v["total"], "ready": v["ready"], "held": v["held"],
                         "requirements": v["requirements"]}
                     for k, v in prog["per_role"].items()},
        "next_unlocks": candidates[:3],
        "permissions": {k: v.as_dict() for k, v in scopes.items()},
        "config": _config(),
    }


async def _load_me(db: AsyncSession, user: User) -> Profile:
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/me")
async def me(user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_me(db, user)
    # Safety net: re-check the status and the automatic unlocks on every visit.
    changed = await cm.refresh_status(db, profile, user)
    new_roles = await cm.check_unlocks(db, profile, user)
    await db.commit()
    payload = await _me_payload(db, profile, user)
    payload["status_changed"] = changed
    payload["new_roles"] = new_roles
    return payload


@router.post("/me/quests/intro_video")
async def intro_video_watched(user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_me(db, user)
    await cm.set_quest(db, profile.id, "intro_video")
    changed = await cm.refresh_status(db, profile, user)
    await db.commit()
    return {"ok": True, "member_status": profile.member_status, "status_changed": changed}


class ConsentBody(BaseModel):
    social: bool


@router.post("/me/consent")
async def consent(body: ConsentBody, user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_me(db, user)
    profile.social_consent = body.social
    profile.social_consent_at = cm.now()
    await db.flush()
    changed = await cm.refresh_status(db, profile, user)
    await db.commit()
    return {"ok": True, "social_consent": body.social, "member_status": profile.member_status,
            "status_changed": changed}


class StoryBody(BaseModel):
    country: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    country_trained: Optional[str] = Field(default=None, max_length=100)
    why_bme: Optional[str] = Field(default=None, max_length=500)


@router.patch("/me/story")
async def story(body: StoryBody, user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_me(db, user)
    for field in ("country", "city", "country_trained", "why_bme"):
        value = getattr(body, field)
        if value is not None:
            setattr(profile, field, value.strip() or None)
    await db.flush()
    changed = await cm.refresh_status(db, profile, user)
    await db.commit()
    return {"ok": True, "member_status": profile.member_status, "status_changed": changed,
            "profile_complete": cm.profile_is_complete(profile)}


class ClaimBody(BaseModel):
    team: Optional[str] = None


@router.post("/me/claim/{role_key}")
async def claim(role_key: str, body: ClaimBody | None = None,
                user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_me(db, user)
    holding = await cm.claim_role(db, profile, role_key, team=(body.team if body else None), user=user)
    await db.commit()
    return {"ok": True, "role_key": holding.role_key, "id": str(holding.id)}


# ── Dashboard: helpers ───────────────────────────────────────

def _in_scope_filter(scope: cm.Scope):
    """SQL condition limiting profiles to the caller's countries or teams."""
    if scope.everywhere:
        return None
    conds = []
    if scope.countries:
        conds.append(Profile.country.in_(scope.countries))
    if scope.teams:
        conds.append(Profile.id.in_(
            select(MemberRole.profile_id).where(MemberRole.status == "active", MemberRole.team.in_(scope.teams))
        ))
    return or_(*conds) if conds else Profile.id.is_(None)


async def _target_in_scope(db: AsyncSession, profile_id: uuid.UUID, scope: cm.Scope) -> Profile:
    target = await db.get(Profile, profile_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not scope.everywhere:
        teams = set((await db.execute(
            select(MemberRole.team).where(MemberRole.profile_id == target.id, MemberRole.status == "active",
                                          MemberRole.team.isnot(None))
        )).scalars().all())
        if not scope.covers(country=target.country, teams=teams):
            raise HTTPException(status_code=403, detail="out_of_scope")
    return target


async def _applicant_row(db: AsyncSession, p: Profile, email: str | None, app: CommunityApplication | None,
                         host_name: str | None, invited_by_name: str | None) -> dict:
    quests = await cm.quests_for(db, p)
    return {
        "id": str(p.id),
        "full_name": p.full_name,
        "username": p.username,
        "email": email,
        "country": p.country,
        "city": p.city,
        "country_trained": p.country_trained,
        "why_bme": p.why_bme,
        "has_photo": bool(p.avatar_key),
        "member_status": p.member_status,
        "join_path": p.join_path,
        "created_at": _iso(p.created_at),
        "invited_by_name": invited_by_name,
        "quests": {q: quests.get(q, 0) >= 1 for q in cm.WELCOME_QUESTS},
        "quests_done": len(cm.quests_done(quests)),
        "quests_total": len(cm.WELCOME_QUESTS),
        "application": {
            "kind": app.kind, "organisation": app.organisation, "motivation": app.motivation,
            "heard_from": app.heard_from, "status": app.status,
            "host_id": str(app.host_id) if app.host_id else None, "host_name": host_name,
            "meeting_at": _iso(app.meeting_at), "meeting_held_at": _iso(app.meeting_held_at),
            "notes": app.notes, "decision_reason": app.decision_reason,
        } if app else None,
    }


async def _load_applicant(db: AsyncSession, profile_id: uuid.UUID, scope: cm.Scope) -> dict:
    p = await _target_in_scope(db, profile_id, scope)
    user = await db.get(User, p.id)
    app = await db.get(CommunityApplication, p.id)
    host_name = None
    if app and app.host_id:
        host_name = await db.scalar(select(Profile.full_name).where(Profile.id == app.host_id))
    inv = None
    if user and user.invited_by:
        inv = await db.scalar(select(Profile.full_name).where(Profile.id == user.invited_by))
    return await _applicant_row(db, p, user.email if user else None, app, host_name, inv)


# ── Dashboard: applicants ────────────────────────────────────

@router.get("/admin/applicants")
async def list_applicants(
    status: str = "pending",
    country: Optional[str] = None,
    ctx=Depends(cm.require_permission("view_applicants")),
    db: AsyncSession = Depends(get_db),
):
    """status: pending (applicants still doing the quests, default), staff,
    refused, or all (everything that isn't a full member yet)."""
    _, scope = ctx
    q = (select(Profile, User.email, User.invited_by)
         .join(User, User.id == Profile.id)
         .where(User.is_active.is_(True)))
    if status == "pending":
        q = q.where(Profile.member_status == "applicant")
    elif status in ("staff", "refused"):
        q = q.where(Profile.member_status == status)
    else:
        q = q.where(Profile.member_status != "member")
    if country:
        q = q.where(Profile.country == country)
    cond = _in_scope_filter(scope)
    if cond is not None:
        q = q.where(cond)
    rows = (await db.execute(q.order_by(Profile.created_at.asc()).limit(500))).all()

    apps = {}
    names = {}
    if rows:
        ids = [r[0].id for r in rows]
        apps = {a.profile_id: a for a in (await db.execute(
            select(CommunityApplication).where(CommunityApplication.profile_id.in_(ids)))).scalars().all()}
        ref_ids = {a.host_id for a in apps.values() if a.host_id} | {r[2] for r in rows if r[2]}
        if ref_ids:
            names = dict((await db.execute(
                select(Profile.id, Profile.full_name).where(Profile.id.in_(ref_ids)))).all())
    items = []
    for p, email, invited_by in rows:
        app = apps.get(p.id)
        items.append(await _applicant_row(
            db, p, email, app,
            names.get(app.host_id) if app and app.host_id else None,
            names.get(invited_by) if invited_by else None,
        ))
    count_q = select(Profile.member_status, func.count()).group_by(Profile.member_status)
    if cond is not None:
        count_q = count_q.where(cond)
    counts = dict((await db.execute(count_q)).all())
    return {"items": items, "status": status, "scope": scope.as_dict(),
            "counts": {k: int(v) for k, v in counts.items()}}


@router.get("/admin/applicants/{profile_id}")
async def get_applicant(profile_id: uuid.UUID, ctx=Depends(cm.require_permission("view_applicants")),
                        db: AsyncSession = Depends(get_db)):
    _, scope = ctx
    return await _load_applicant(db, profile_id, scope)


async def _get_or_create_app(db: AsyncSession, profile_id) -> CommunityApplication:
    app = await db.get(CommunityApplication, profile_id)
    if app is None:
        # Accounts created before /join (OAuth, /signup, a clinic invite) have no row yet.
        app = CommunityApplication(profile_id=profile_id, kind="other", status="open")
        db.add(app)
        await db.flush()
    return app


class ApplicantPatch(BaseModel):
    host_id: Optional[str] = None
    meeting_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=4000)
    clear_meeting: bool = False


@router.patch("/admin/applicants/{profile_id}")
async def patch_applicant(profile_id: uuid.UUID, body: ApplicantPatch,
                          ctx=Depends(cm.require_permission("decide_applicants")),
                          db: AsyncSession = Depends(get_db)):
    actor, scope = ctx
    target = await _target_in_scope(db, profile_id, scope)
    app = await _get_or_create_app(db, target.id)
    before = {"host_id": str(app.host_id) if app.host_id else None, "meeting_at": _iso(app.meeting_at)}
    if body.host_id is not None:
        if body.host_id == "":
            app.host_id = None
        else:
            try:
                host_uuid = uuid.UUID(body.host_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid_host")
            if not await db.get(Profile, host_uuid):
                raise HTTPException(status_code=400, detail="invalid_host")
            app.host_id = host_uuid
    if body.clear_meeting:
        app.meeting_at = None
    elif body.meeting_at is not None:
        app.meeting_at = body.meeting_at
    if body.notes is not None:
        app.notes = body.notes.strip() or None
    if app.status == "open" and app.meeting_at:
        app.status = "meeting_booked"
    elif app.status == "meeting_booked" and not app.meeting_at:
        app.status = "open"
    app.updated_at = cm.now()
    await cm.log_change(db, actor.id, "applicant_updated", str(target.id), before=before,
                        after={"host_id": str(app.host_id) if app.host_id else None,
                               "meeting_at": _iso(app.meeting_at)})
    await db.commit()
    return await _load_applicant(db, profile_id, scope)


@router.post("/admin/applicants/{profile_id}/meeting-held")
async def meeting_held(profile_id: uuid.UUID, ctx=Depends(cm.require_permission("decide_applicants")),
                       db: AsyncSession = Depends(get_db)):
    actor, scope = ctx
    target = await _target_in_scope(db, profile_id, scope)
    if target.member_status == "refused":
        raise HTTPException(status_code=400, detail="applicant_refused")
    app = await _get_or_create_app(db, target.id)
    app.meeting_held_at = cm.now()
    app.meeting_confirmed_by = actor.id
    if app.host_id is None:
        app.host_id = actor.id
    app.status = "met"
    await cm.set_quest(db, target.id, "meeting_held", confirmed_by=actor.id)
    await cm.log_change(db, actor.id, "meeting_held", str(target.id))
    changed = await cm.refresh_status(db, target, actor_id=actor.id)
    await db.commit()
    out = await _load_applicant(db, profile_id, scope)
    out["status_changed"] = changed
    return out


@router.post("/admin/applicants/{profile_id}/quests/{quest_key}")
async def confirm_quest(profile_id: uuid.UUID, quest_key: str,
                        ctx=Depends(cm.require_permission("confirm_quests")),
                        db: AsyncSession = Depends(get_db)):
    """Mark a quest a person can vouch for, e.g. Discord joined when the
    applicant joined without linking their account. The meeting has its own
    route (it needs decide_applicants)."""
    actor, scope = ctx
    if quest_key not in cm.CONFIRMABLE_QUESTS or quest_key == "meeting_held":
        raise HTTPException(status_code=400, detail="quest_not_confirmable")
    target = await _target_in_scope(db, profile_id, scope)
    await cm.set_quest(db, target.id, quest_key, confirmed_by=actor.id)
    await cm.log_change(db, actor.id, "quest_confirmed", str(target.id), after={"quest": quest_key})
    changed = await cm.refresh_status(db, target, actor_id=actor.id)
    await db.commit()
    out = await _load_applicant(db, profile_id, scope)
    out["status_changed"] = changed
    return out


class ReasonBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


@router.post("/admin/applicants/{profile_id}/refuse")
async def refuse(profile_id: uuid.UUID, body: ReasonBody,
                 ctx=Depends(cm.require_permission("decide_applicants")),
                 db: AsyncSession = Depends(get_db)):
    actor, scope = ctx
    target = await _target_in_scope(db, profile_id, scope)
    if target.member_status == "member":
        raise HTTPException(status_code=400, detail="already_member")
    app = await _get_or_create_app(db, target.id)
    before = {"member_status": target.member_status}
    target.member_status = "refused"
    app.status = "refused"
    app.decision_reason = body.reason.strip()
    await cm.log_change(db, actor.id, "applicant_refused", str(target.id), before=before,
                        after={"member_status": "refused"}, reason=app.decision_reason)
    await db.commit()
    return await _load_applicant(db, profile_id, scope)


@router.post("/admin/applicants/{profile_id}/reopen")
async def reopen(profile_id: uuid.UUID, ctx=Depends(cm.require_permission("decide_applicants")),
                 db: AsyncSession = Depends(get_db)):
    actor, scope = ctx
    target = await _target_in_scope(db, profile_id, scope)
    if target.member_status != "refused":
        raise HTTPException(status_code=400, detail="not_refused")
    app = await _get_or_create_app(db, target.id)
    target.member_status = "applicant"
    app.status = "met" if app.meeting_held_at else ("meeting_booked" if app.meeting_at else "open")
    app.decision_reason = None
    await cm.log_change(db, actor.id, "applicant_reopened", str(target.id),
                        before={"member_status": "refused"}, after={"member_status": "applicant"})
    await cm.refresh_status(db, target, actor_id=actor.id)
    await db.commit()
    return await _load_applicant(db, profile_id, scope)


@router.get("/admin/hosts")
async def hosts(ctx=Depends(cm.require_permission("view_applicants")), db: AsyncSession = Depends(get_db)):
    """People who can host a welcome meeting: holders of a role granting
    decide_applicants, plus superusers."""
    role_keys = select(CommunityRolePermission.role_key).where(
        CommunityRolePermission.permission == "decide_applicants")
    rows = (await db.execute(
        select(Profile.id, Profile.full_name, Profile.country)
        .join(User, User.id == Profile.id)
        .where(User.is_active.is_(True), or_(
            User.is_superuser.is_(True),
            Profile.id.in_(select(MemberRole.profile_id).where(
                MemberRole.status == "active", MemberRole.role_key.in_(role_keys))),
        ))
        .order_by(Profile.full_name)
    )).all()
    return [{"id": str(i), "full_name": n, "country": c} for i, n, c in rows]


# ── Dashboard: members ───────────────────────────────────────

@router.get("/admin/members")
async def list_members(
    q: Optional[str] = None,
    role: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ctx=Depends(cm.require_permission("view_members")),
    db: AsyncSession = Depends(get_db),
):
    _, scope = ctx
    from routers.profile import _metric_subqueries
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    subs, metrics = _metric_subqueries()
    base = (
        select(Profile, User.email, *metrics)
        .join(User, User.id == Profile.id)
        .outerjoin(subs[0], subs[0].c.pid == Profile.id)
        .outerjoin(subs[1], subs[1].c.pid == Profile.id)
        .outerjoin(subs[2], subs[2].c.pid == Profile.id)
        .outerjoin(subs[3], subs[3].c.pid == Profile.id)
        .where(User.is_active.is_(True), Profile.member_status == "member")
    )
    if q and q.strip():
        needle = f"%{q.strip()}%"
        base = base.where(or_(Profile.full_name.ilike(needle), Profile.username.ilike(needle),
                              Profile.city.ilike(needle)))
    if country:
        base = base.where(Profile.country == country)
    if role:
        base = base.where(Profile.id.in_(select(MemberRole.profile_id).where(
            MemberRole.role_key == role, MemberRole.status == "active")))
    cond = _in_scope_filter(scope)
    if cond is not None:
        base = base.where(cond)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(
        base.order_by(Profile.last_active_at.desc().nulls_last(), Profile.full_name).limit(limit).offset(offset)
    )).all()

    catalogue = {r["key"]: r for r in await cm.load_catalogue(db, include_inactive=True)}
    ids = [r[0].id for r in rows]
    holdings: dict = {}
    if ids:
        for h in (await db.execute(select(MemberRole).where(
                MemberRole.profile_id.in_(ids), MemberRole.status == "active")
                .order_by(MemberRole.granted_at))).scalars().all():
            holdings.setdefault(h.profile_id, []).append(h)
    items = []
    for p, email, dev_n, rep_n, mnt_n, inv_n in rows:
        paused = cm.is_paused(p.last_active_at)
        items.append({
            "id": str(p.id), "full_name": p.full_name, "username": p.username,
            "email": email, "country": p.country, "city": p.city,
            "member_since": _iso(p.member_since), "last_active_at": _iso(p.last_active_at),
            "paused": paused,
            "roles": [_holding_out(h, catalogue, paused) for h in holdings.get(p.id, [])],
            "devices_registered": int(dev_n), "faults_resolved": int(rep_n),
            "maintenance_performed": int(mnt_n), "invites": int(inv_n),
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset, "scope": scope.as_dict()}


def _change_out(c: CommunityRoleChange, names: dict) -> dict:
    return {
        "id": str(c.id), "actor_id": str(c.actor_id) if c.actor_id else None,
        "actor_name": names.get(c.actor_id), "action": c.action, "target": c.target,
        "target_name": names.get(_as_uuid(c.target)), "before": c.before, "after": c.after,
        "reason": c.reason, "created_at": _iso(c.created_at),
    }


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


async def _names_for(db: AsyncSession, changes) -> dict:
    ids = {c.actor_id for c in changes if c.actor_id} | {u for c in changes if (u := _as_uuid(c.target))}
    if not ids:
        return {}
    return dict((await db.execute(select(Profile.id, Profile.full_name).where(Profile.id.in_(ids)))).all())


@router.get("/admin/members/{profile_id}")
async def get_member(profile_id: uuid.UUID, ctx=Depends(cm.require_permission("view_members")),
                     db: AsyncSession = Depends(get_db)):
    viewer, scope = ctx
    target = await _target_in_scope(db, profile_id, scope)
    user = await db.get(User, target.id)
    catalogue = {r["key"]: r for r in await cm.load_catalogue(db, include_inactive=True)}
    paused = cm.is_paused(target.last_active_at)
    holdings = (await db.execute(select(MemberRole).where(MemberRole.profile_id == target.id)
                                 .order_by(MemberRole.granted_at.desc()))).scalars().all()
    changes = (await db.execute(select(CommunityRoleChange)
                                .where(CommunityRoleChange.target == str(target.id))
                                .order_by(CommunityRoleChange.created_at.desc()).limit(100))).scalars().all()
    names = await _names_for(db, changes)
    granted_by = {h.granted_by for h in holdings if h.granted_by}
    if granted_by:
        names.update(dict((await db.execute(
            select(Profile.id, Profile.full_name).where(Profile.id.in_(granted_by)))).all()))
    metrics = await cm.metrics_for(db, target.id)
    viewer_scopes = await cm.permission_scopes(db, viewer)
    return {
        "id": str(target.id), "full_name": target.full_name, "username": target.username,
        "email": user.email if user else None, "country": target.country, "city": target.city,
        "country_trained": target.country_trained, "why_bme": target.why_bme,
        "member_status": target.member_status, "member_since": _iso(target.member_since),
        "last_active_at": _iso(target.last_active_at), "paused": paused,
        "social_consent": target.social_consent,
        "roles": [{**_holding_out(h, catalogue, paused),
                   "granted_by_name": names.get(h.granted_by)} for h in holdings],
        "history": [_change_out(c, names) for c in changes],
        "metrics": metrics,
        "can_assign": "assign_roles" in viewer_scopes,
    }


class AssignBody(BaseModel):
    role_key: str
    country: Optional[str] = None
    team: Optional[str] = None
    reason: Optional[str] = Field(default=None, max_length=2000)


@router.post("/admin/members/{profile_id}/roles")
async def assign_role(profile_id: uuid.UUID, body: AssignBody,
                      ctx=Depends(cm.require_permission("assign_roles")),
                      db: AsyncSession = Depends(get_db)):
    actor, scope = ctx
    target = await _target_in_scope(db, profile_id, scope)
    if target.member_status != "member":
        raise HTTPException(status_code=400, detail="not_a_member")
    role = await db.get(CommunityRole, body.role_key)
    if role is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    if role.scope == "global" and body.team not in cm.TEAMS:
        raise HTTPException(status_code=400, detail="team_required")
    holding = await cm.grant_role(db, target, role.key, source="assigned", granted_by=actor.id,
                                  country=body.country, team=body.team, reason=body.reason)
    await db.commit()
    return {"ok": True, "id": str(holding.id)}


@router.delete("/admin/member-roles/{holding_id}")
async def remove_member_role(holding_id: uuid.UUID, reason: str = Query(min_length=1, max_length=2000),
                             ctx=Depends(cm.require_permission("assign_roles")),
                             db: AsyncSession = Depends(get_db)):
    actor, scope = ctx
    holding = await db.get(MemberRole, holding_id)
    if holding is None or holding.status != "active":
        raise HTTPException(status_code=404, detail="role_not_found")
    await _target_in_scope(db, holding.profile_id, scope)
    await cm.remove_role(db, holding, actor.id, reason.strip())
    await db.commit()
    return {"ok": True}


# ── Dashboard: permissions and history ───────────────────────

@router.get("/admin/permissions")
async def permissions(user: User = Depends(current_active_user), db: AsyncSession = Depends(get_db)):
    profile = await _load_me(db, user)
    mine = await cm.permission_scopes(db, profile, user)
    if not any(k in mine for k in ("view_applicants", "view_members", "assign_roles",
                                   "manage_roles", "view_role_history")):
        raise HTTPException(status_code=403, detail="missing_permission")
    granted = {}
    for role_key, perm in (await db.execute(
            select(CommunityRolePermission.role_key, CommunityRolePermission.permission))).all():
        granted.setdefault(perm, []).append(role_key)
    return [{"key": k, "group": v["group"], "en": v["en"], "checked": v["checked"],
             "roles": sorted(granted.get(k, []))} for k, v in cm.PERMISSIONS.items()]


@router.get("/admin/history")
async def history(limit: int = 100, offset: int = 0,
                  ctx=Depends(cm.require_permission("view_role_history")),
                  db: AsyncSession = Depends(get_db)):
    limit = max(1, min(limit, 500))
    changes = (await db.execute(select(CommunityRoleChange)
                                .order_by(CommunityRoleChange.created_at.desc())
                                .limit(limit).offset(max(0, offset)))).scalars().all()
    names = await _names_for(db, changes)
    return {"items": [_change_out(c, names) for c in changes], "limit": limit, "offset": offset}
