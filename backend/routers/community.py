# routers/community.py — community journey API, mounted at /api/community
#
# Guide: docs/docs/community-guide.md. Rules: utils/community.py.
#
#   Public
#     GET  /catalogue                the teams and achievements, with counts
#     GET  /config                   booking link, video and Discord URLs
#     POST /join                     create an account (a community applicant) → {access_token}
#     GET  /public/stats             members per country (for fixmymedtech.org)
#   Signed in (any status, so applicants can do their quests)
#     GET  /me                       status, welcome quests, teams, achievements, powers
#     POST /me/quests/intro_video    the intro video was watched
#     POST /me/consent               {social: true|false}
#     PATCH /me/story                city, country, country trained in, why biomedical engineering
#   Community admin (who may do what: utils/community.py powers_from)
#     GET   /admin/applicants                       Community Builders
#     GET   /admin/applicants/{id}
#     PATCH /admin/applicants/{id}                  host, call time, notes
#     POST  /admin/applicants/{id}/meeting-held     completes the meeting quest
#     POST  /admin/applicants/{id}/quests/{key}     e.g. discord_joined without Discord login
#     POST  /admin/applicants/{id}/refuse
#     POST  /admin/applicants/{id}/reopen
#     GET   /admin/hosts                            who can host a welcome call
#     GET   /admin/members                          any team member or lead
#     GET   /admin/members/{id}
#     POST  /admin/members/{id}/teams               {team_key, level, reason}
#     DELETE /admin/team-members/{id}?reason=
#     POST  /admin/members/{id}/achievements        {achievement_key, count, note}
#     DELETE /admin/achievement-records/{id}?reason=
#     PATCH /admin/teams/{key}                      team texts (its lead, or a superuser)
#     GET   /admin/history                          leads and superusers
#
# Every response is built by hand from columns. Never return ORM rows:
# Profile.user is selectin-loaded and would leak hashed_password.

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.users import current_active_user, get_user_manager, UserManager, get_jwt_strategy
from models.models import (
    User, Profile, Organization, OrgUser, CommunityTeam, TeamMember, Achievement,
    AchievementRecord, CommunityApplication, CommunityChange,
)
from utils import community as cm
from utils.username import generate_username

router = APIRouter()

KINDS = ("engineer", "student", "clinician", "other")
LANGS = ("en", "fr", "es")

can_view_applicants = cm.require_power(lambda p: p.view_applicants)
can_decide = cm.require_power(lambda p: p.decide_applicants)
can_confirm = cm.require_power(lambda p: p.confirm_quests)
can_view_members = cm.require_power(lambda p: p.view_members)
can_view_history = cm.require_power(lambda p: p.view_history)
signed_in_powers = cm.require_power(lambda p: True)


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


def _place_out(m: TeamMember, paused: bool = False, names: dict | None = None) -> dict:
    return {
        "id": str(m.id), "team_key": m.team_key, "level": m.level, "status": m.status,
        "paused": paused, "granted_at": _iso(m.granted_at),
        "granted_by_name": (names or {}).get(m.granted_by),
        "removed_at": _iso(m.removed_at), "removed_reason": m.removed_reason,
    }


async def _welcome_quests(profile: Profile, quests: dict) -> list[dict]:
    checked_by = {
        "profile_complete": "auto", "intro_video": "auto", "meeting_held": "host",
        "discord_joined": "auto", "consent_answered": "auto",
    }
    return [{"key": q, "done": quests.get(q, 0) >= 1, "checked": checked_by[q]} for q in cm.WELCOME_QUESTS]


# ── Public ───────────────────────────────────────────────────

@router.get("/catalogue")
async def catalogue(db: AsyncSession = Depends(get_db)):
    teams = await cm.load_teams(db)
    achievements = await cm.load_achievements(db)
    per_team = {}
    for team, level, n in (await db.execute(
            select(TeamMember.team_key, TeamMember.level, func.count())
            .where(TeamMember.status == "active")
            .group_by(TeamMember.team_key, TeamMember.level))).all():
        per_team.setdefault(team, {})[level] = int(n)
    earners = dict((await db.execute(
        select(AchievementRecord.achievement_key, func.count(func.distinct(AchievementRecord.profile_id)))
        .group_by(AchievementRecord.achievement_key))).all())
    return {
        "teams": [{**t, "counts": per_team.get(t["key"], {})} for t in teams],
        "achievements": [{**a, "earners": int(earners.get(a["key"], 0))} for a in achievements],
        "levels": list(cm.LEVELS),
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
    quests = await cm.quests_for(db, profile, user)
    metrics = await cm.metrics_for(db, profile.id)
    paused = cm.is_paused(profile.last_active_at)
    places = await cm.team_places(db, profile.id)
    powers = await cm.powers_for(db, profile, user)
    app = await db.get(CommunityApplication, profile.id)
    host_name = None
    if app and app.host_id:
        host_name = await db.scalar(select(Profile.full_name).where(Profile.id == app.host_id))
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
        "welcome_quests": await _welcome_quests(profile, quests),
        "application": {
            "status": app.status, "kind": app.kind,
            "meeting_at": _iso(app.meeting_at), "meeting_held_at": _iso(app.meeting_held_at),
            "host_name": host_name,
            "decision_reason": app.decision_reason if app.status == "refused" else None,
        } if app else None,
        "teams": [_place_out(m, paused) for m in places],
        "achievements": await cm.achievement_progress(db, profile.id, metrics=metrics),
        "paused": paused,
        "metrics": metrics,
        "permissions": powers.as_list(),
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
    # Safety net: re-check the status on every visit.
    changed = await cm.refresh_status(db, profile, user)
    await db.commit()
    payload = await _me_payload(db, profile, user)
    payload["status_changed"] = changed
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


# ── Dashboard: helpers ───────────────────────────────────────

async def _target(db: AsyncSession, profile_id: uuid.UUID) -> Profile:
    target = await db.get(Profile, profile_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Profile not found")
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


async def _load_applicant(db: AsyncSession, profile_id: uuid.UUID) -> dict:
    p = await _target(db, profile_id)
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
    ctx=Depends(can_view_applicants),
    db: AsyncSession = Depends(get_db),
):
    """status: pending (applicants still doing the quests, default), staff,
    refused, or all (everything that isn't a full member yet)."""
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
    counts = dict((await db.execute(count_q)).all())
    return {"items": items, "status": status,
            "counts": {k: int(v) for k, v in counts.items()}}


@router.get("/admin/applicants/{profile_id}")
async def get_applicant(profile_id: uuid.UUID, ctx=Depends(can_view_applicants),
                        db: AsyncSession = Depends(get_db)):
    return await _load_applicant(db, profile_id)


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
                          ctx=Depends(can_decide),
                          db: AsyncSession = Depends(get_db)):
    actor, _ = ctx
    target = await _target(db, profile_id)
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
    return await _load_applicant(db, profile_id)


@router.post("/admin/applicants/{profile_id}/meeting-held")
async def meeting_held(profile_id: uuid.UUID, ctx=Depends(can_decide),
                       db: AsyncSession = Depends(get_db)):
    actor, _ = ctx
    target = await _target(db, profile_id)
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
    out = await _load_applicant(db, profile_id)
    out["status_changed"] = changed
    return out


@router.post("/admin/applicants/{profile_id}/quests/{quest_key}")
async def confirm_quest(profile_id: uuid.UUID, quest_key: str,
                        ctx=Depends(can_confirm),
                        db: AsyncSession = Depends(get_db)):
    """Mark a quest a person can vouch for, e.g. Discord joined when the
    applicant joined without linking their account. The meeting has its own
    route (it needs decide_applicants)."""
    actor, _ = ctx
    if quest_key not in cm.CONFIRMABLE_QUESTS or quest_key == "meeting_held":
        raise HTTPException(status_code=400, detail="quest_not_confirmable")
    target = await _target(db, profile_id)
    await cm.set_quest(db, target.id, quest_key, confirmed_by=actor.id)
    await cm.log_change(db, actor.id, "quest_confirmed", str(target.id), after={"quest": quest_key})
    changed = await cm.refresh_status(db, target, actor_id=actor.id)
    await db.commit()
    out = await _load_applicant(db, profile_id)
    out["status_changed"] = changed
    return out


class ReasonBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


@router.post("/admin/applicants/{profile_id}/refuse")
async def refuse(profile_id: uuid.UUID, body: ReasonBody,
                 ctx=Depends(can_decide),
                 db: AsyncSession = Depends(get_db)):
    actor, _ = ctx
    target = await _target(db, profile_id)
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
    return await _load_applicant(db, profile_id)


@router.post("/admin/applicants/{profile_id}/reopen")
async def reopen(profile_id: uuid.UUID, ctx=Depends(can_decide),
                 db: AsyncSession = Depends(get_db)):
    actor, _ = ctx
    target = await _target(db, profile_id)
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
    return await _load_applicant(db, profile_id)


@router.get("/admin/hosts")
async def hosts(ctx=Depends(can_view_applicants), db: AsyncSession = Depends(get_db)):
    """People who can host a welcome call: Community Builder members and
    leads, plus superusers."""
    rows = (await db.execute(
        select(Profile.id, Profile.full_name, Profile.country)
        .join(User, User.id == Profile.id)
        .where(User.is_active.is_(True), or_(
            User.is_superuser.is_(True),
            Profile.id.in_(select(TeamMember.profile_id).where(
                TeamMember.status == "active", TeamMember.team_key == cm.WELCOMING_TEAM,
                TeamMember.level.in_(("member", "lead")))),
        ))
        .order_by(Profile.full_name)
    )).all()
    return [{"id": str(i), "full_name": n, "country": c} for i, n, c in rows]


# ── Dashboard: members ───────────────────────────────────────

@router.get("/admin/members")
async def list_members(
    q: Optional[str] = None,
    team: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ctx=Depends(can_view_members),
    db: AsyncSession = Depends(get_db),
):
    """Members, most recently active first. team filters on an active place
    in that team (any level)."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    base = (
        select(Profile, User.email)
        .join(User, User.id == Profile.id)
        .where(User.is_active.is_(True), Profile.member_status == "member")
    )
    if q and q.strip():
        needle = f"%{q.strip()}%"
        base = base.where(or_(Profile.full_name.ilike(needle), Profile.username.ilike(needle),
                              Profile.city.ilike(needle)))
    if country:
        base = base.where(Profile.country == country)
    if team:
        base = base.where(Profile.id.in_(select(TeamMember.profile_id).where(
            TeamMember.team_key == team, TeamMember.status == "active")))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(
        base.order_by(Profile.last_active_at.desc().nulls_last(), Profile.full_name).limit(limit).offset(offset)
    )).all()

    achievements = await cm.load_achievements(db)
    ids = [r[0].id for r in rows]
    places: dict = {}
    if ids:
        for m in (await db.execute(select(TeamMember).where(
                TeamMember.profile_id.in_(ids), TeamMember.status == "active")
                .order_by(TeamMember.granted_at))).scalars().all():
            places.setdefault(m.profile_id, []).append(m)
    items = []
    for p, email in rows:
        paused = cm.is_paused(p.last_active_at)
        stars = await cm.achievement_progress(db, p.id, achievements)
        items.append({
            "id": str(p.id), "full_name": p.full_name, "username": p.username,
            "email": email, "country": p.country, "city": p.city,
            "member_since": _iso(p.member_since), "last_active_at": _iso(p.last_active_at),
            "paused": paused,
            "teams": [_place_out(m, paused) for m in places.get(p.id, [])],
            "achievements": [a for a in stars if a["level"] > 0],
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def _change_out(c: CommunityChange, names: dict) -> dict:
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


async def _names(db: AsyncSession, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict((await db.execute(select(Profile.id, Profile.full_name).where(Profile.id.in_(ids)))).all())


async def _names_for(db: AsyncSession, changes) -> dict:
    return await _names(db, {c.actor_id for c in changes} | {_as_uuid(c.target) for c in changes})


@router.get("/admin/members/{profile_id}")
async def get_member(profile_id: uuid.UUID, ctx=Depends(can_view_members),
                     db: AsyncSession = Depends(get_db)):
    _, powers = ctx
    target = await _target(db, profile_id)
    user = await db.get(User, target.id)
    paused = cm.is_paused(target.last_active_at)
    places = (await db.execute(select(TeamMember).where(TeamMember.profile_id == target.id)
                               .order_by(TeamMember.granted_at.desc()))).scalars().all()
    records = (await db.execute(select(AchievementRecord).where(AchievementRecord.profile_id == target.id)
                                .order_by(AchievementRecord.created_at.desc()).limit(200))).scalars().all()
    changes = (await db.execute(select(CommunityChange)
                                .where(CommunityChange.target == str(target.id))
                                .order_by(CommunityChange.created_at.desc()).limit(100))).scalars().all()
    names = await _names_for(db, changes)
    names.update(await _names(db, {m.granted_by for m in places} | {r.recognised_by for r in records}))
    metrics = await cm.metrics_for(db, target.id)
    return {
        "id": str(target.id), "full_name": target.full_name, "username": target.username,
        "email": user.email if user else None, "country": target.country, "city": target.city,
        "country_trained": target.country_trained, "why_bme": target.why_bme,
        "member_status": target.member_status, "member_since": _iso(target.member_since),
        "last_active_at": _iso(target.last_active_at), "paused": paused,
        "social_consent": target.social_consent,
        "teams": [_place_out(m, paused, names) for m in places],
        "achievements": await cm.achievement_progress(db, target.id, metrics=metrics),
        "records": [{"id": str(r.id), "achievement_key": r.achievement_key, "count": r.count,
                     "note": r.note, "recognised_by_name": names.get(r.recognised_by),
                     "created_at": _iso(r.created_at)} for r in records],
        "history": [_change_out(c, names) for c in changes],
        "metrics": metrics,
        "can": powers.as_list(),
    }


class TeamBody(BaseModel):
    team_key: str
    level: str = "candidate"
    reason: Optional[str] = Field(default=None, max_length=2000)


@router.post("/admin/members/{profile_id}/teams")
async def add_to_team(profile_id: uuid.UUID, body: TeamBody, ctx=Depends(signed_in_powers),
                      db: AsyncSession = Depends(get_db)):
    """Put a member in a team, or change their level there."""
    actor, powers = ctx
    if body.level not in cm.LEVELS:
        raise HTTPException(status_code=400, detail="invalid_level")
    team = await db.get(CommunityTeam, body.team_key)
    if team is None or not team.active:
        raise HTTPException(status_code=404, detail="team_not_found")
    if not powers.can_add(team.key, body.level):
        raise HTTPException(status_code=403, detail="missing_permission")
    target = await _target(db, profile_id)
    if target.member_status != "member":
        raise HTTPException(status_code=400, detail="not_a_member")
    current = await db.scalar(select(TeamMember).where(
        TeamMember.profile_id == target.id, TeamMember.team_key == team.key, TeamMember.status == "active"))
    if current is not None and not powers.can_remove(team.key, current.level):
        # e.g. a Community Builder can't turn a member back into a candidate.
        raise HTTPException(status_code=403, detail="missing_permission")
    place = await cm.set_team_place(db, target, team.key, body.level, granted_by=actor.id,
                                    reason=(body.reason or "").strip() or None)
    await db.commit()
    return {"ok": True, "id": str(place.id)}


@router.delete("/admin/team-members/{place_id}")
async def remove_from_team(place_id: uuid.UUID, reason: str = Query(min_length=1, max_length=2000),
                           ctx=Depends(signed_in_powers), db: AsyncSession = Depends(get_db)):
    actor, powers = ctx
    place = await db.get(TeamMember, place_id)
    if place is None or place.status != "active":
        raise HTTPException(status_code=404, detail="place_not_found")
    if not powers.can_remove(place.team_key, place.level):
        raise HTTPException(status_code=403, detail="missing_permission")
    await cm.remove_team_place(db, place, actor.id, reason.strip())
    await db.commit()
    return {"ok": True}


class RecogniseBody(BaseModel):
    achievement_key: str
    count: int = Field(default=1, ge=1, le=100)
    note: Optional[str] = Field(default=None, max_length=1000)


@router.post("/admin/members/{profile_id}/achievements")
async def recognise(profile_id: uuid.UUID, body: RecogniseBody, ctx=Depends(signed_in_powers),
                    db: AsyncSession = Depends(get_db)):
    """A team member records an achievement of their team's category, e.g. a
    Community Builder records that Amina helped an engineer (Supporter)."""
    actor, powers = ctx
    ach = await db.get(Achievement, body.achievement_key)
    if ach is None or not ach.active:
        raise HTTPException(status_code=404, detail="achievement_not_found")
    if ach.source != "recognised":
        raise HTTPException(status_code=400, detail="achievement_is_automatic")
    if ach.team_key not in powers.recognise:
        raise HTTPException(status_code=403, detail="missing_permission")
    target = await _target(db, profile_id)
    if target.member_status != "member":
        raise HTTPException(status_code=400, detail="not_a_member")
    if target.id == actor.id and not powers.superuser:
        raise HTTPException(status_code=400, detail="not_for_yourself")
    record = await cm.recognise(db, target.id, ach.key, body.count,
                                (body.note or "").strip() or None, actor.id)
    await db.commit()
    return {"ok": True, "id": str(record.id)}


@router.delete("/admin/achievement-records/{record_id}")
async def remove_record(record_id: uuid.UUID, reason: str = Query(min_length=1, max_length=2000),
                        ctx=Depends(signed_in_powers), db: AsyncSession = Depends(get_db)):
    """Undo a recognition made by mistake: its author, a lead of its team, or a superuser."""
    actor, powers = ctx
    record = await db.get(AchievementRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="record_not_found")
    ach = await db.get(Achievement, record.achievement_key)
    team = ach.team_key if ach else None
    if not (powers.superuser or team in powers.manage_members
            or (record.recognised_by == actor.id and team in powers.recognise)):
        raise HTTPException(status_code=403, detail="missing_permission")
    await cm.log_change(db, actor.id, "achievement_removed", str(record.profile_id),
                        before={"achievement": record.achievement_key, "count": record.count},
                        reason=reason.strip())
    await db.delete(record)
    await db.commit()
    return {"ok": True}


# ── Dashboard: teams and history ─────────────────────────────

class TeamTexts(BaseModel):
    names: Optional[dict[str, str]] = None
    descriptions: Optional[dict[str, str]] = None
    linkedin_titles: Optional[dict[str, str]] = None
    tasks: Optional[dict[str, list[str]]] = None


@router.patch("/admin/teams/{team_key}")
async def edit_team(team_key: str, body: TeamTexts, ctx=Depends(signed_in_powers),
                    db: AsyncSession = Depends(get_db)):
    """A team's lead edits what the team page says, in each language."""
    actor, powers = ctx
    team = await db.get(CommunityTeam, team_key)
    if team is None:
        raise HTTPException(status_code=404, detail="team_not_found")
    if team_key not in powers.edit_team:
        raise HTTPException(status_code=403, detail="missing_permission")
    before = cm.team_out(team)
    for field in ("names", "descriptions", "linkedin_titles"):
        value = getattr(body, field)
        if value is not None:
            clean = {k: v.strip()[:1000] for k, v in value.items() if k in LANGS and v and v.strip()}
            if field == "names" and "en" not in clean:
                raise HTTPException(status_code=400, detail="name_required")
            setattr(team, field, clean)
    if body.tasks is not None:
        team.tasks = {k: [line.strip()[:300] for line in v if line.strip()][:20]
                      for k, v in body.tasks.items() if k in LANGS}
    team.updated_by = actor.id
    team.updated_at = cm.now()
    after = cm.team_out(team)
    await cm.log_change(db, actor.id, "team_edited", team_key,
                        before={k: before[k] for k in ("names", "descriptions")},
                        after={k: after[k] for k in ("names", "descriptions")})
    await db.commit()
    return after


@router.get("/admin/history")
async def history(limit: int = 100, offset: int = 0, ctx=Depends(can_view_history),
                  db: AsyncSession = Depends(get_db)):
    limit = max(1, min(limit, 500))
    changes = (await db.execute(select(CommunityChange)
                                .order_by(CommunityChange.created_at.desc())
                                .limit(limit).offset(max(0, offset)))).scalars().all()
    names = await _names_for(db, changes)
    return {"items": [_change_out(c, names) for c in changes], "limit": limit, "offset": offset}
