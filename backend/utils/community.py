# utils/community.py — the community journey engine (skill tree of community roles)
#
# Community roles (Ambassador, Mapper, Repairer, City lead…) are not org roles.
# org_users.role decides what someone can do inside one organization; a
# community role is what a member is in the community, and it grants
# community PERMISSIONS. Plan: docs/docs/community-journey.md
#
# The split of responsibilities:
#   - The code answers "what can be done": the PERMISSIONS keys below, each
#     checked by a router with require_permission(...).
#   - The database answers "who can do it": community_role_permissions says
#     which role grants which key, and admins edit it.
#
# Pure helpers (requirement_status, is_paused, quests_done) have no database
# access, so the rules can be unit-tested (backend/tests/test_community.py).

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.users import current_active_user
from models.models import (
    User, Profile, Device, FaultReport, MaintenanceLog, Document,
    CommunityRole, CommunityRoleRequirement, CommunityRolePermission,
    MemberRole, MemberQuest, CommunityApplication, CommunityRoleChange,
)

# ── Permission keys ──────────────────────────────────────────
# Adding a role made of these keys needs no code. A new KIND of access needs
# a new key here plus one require_permission("key") on the router that does
# the action. `checked` says whether a router enforces the key yet.

PERMISSIONS: dict[str, dict] = {
    # Community admin dashboard
    "view_applicants":   {"group": "admin", "checked": True,  "en": "See applicants and their quests (in your country)"},
    "decide_applicants": {"group": "admin", "checked": True,  "en": "Assign a host, record the welcome meeting, refuse an applicant"},
    "view_members":      {"group": "admin", "checked": True,  "en": "See members, their roles and actions (in your country or team)"},
    "assign_roles":      {"group": "admin", "checked": True,  "en": "Give or remove any community role (community team admins)"},
    "manage_roles":      {"group": "admin", "checked": True,  "en": "Edit the skill tree and its permissions (community team admins)"},
    "view_role_history": {"group": "admin", "checked": True,  "en": "See the history of role and applicant changes"},
    "confirm_quests":    {"group": "community", "checked": True, "en": "Confirm a quest another member did, e.g. Discord joined or a watched meeting"},
    # Community
    "claim_verification_tasks": {"group": "community", "checked": False, "en": "Pick up verification tasks on the community task board"},
    "approve_clinics":   {"group": "community", "checked": False, "en": "Approve or refuse pending clinics"},
    "invite_clinics":    {"group": "community", "checked": False, "en": "Send invitation links to clinics"},
    "create_local_tasks": {"group": "community", "checked": False, "en": "Create community tasks for your country"},
    "approve_team_contributions": {"group": "community", "checked": False, "en": "Approve contributions in your global team"},
    # Devices and repairs
    "register_devices_for_clinics": {"group": "devices", "checked": False, "en": "Register devices at any approved clinic that asks for help"},
    "receive_area_repair_requests": {"group": "devices", "checked": False, "en": "Receive repair requests from the maintenance button in your area"},
    "diagnose_outside_my_orgs":     {"group": "devices", "checked": False, "en": "Diagnose and repair faults at clinics that are not yours"},
    "plan_clinic_maintenance":      {"group": "devices", "checked": False, "en": "Plan preventive maintenance for a whole clinic"},
    "add_manuals":       {"group": "knowledge", "checked": False, "en": "Add and link manuals to models"},
    "approve_manuals":   {"group": "knowledge", "checked": False, "en": "Approve manuals and guides others added"},
    "merge_entries":     {"group": "knowledge", "checked": False, "en": "Merge duplicate brands and models"},
    # Spare parts (wait for the parts library and catalogue)
    "order_spare_parts":       {"group": "parts", "checked": False, "en": "Order from the spare parts catalogue (Repairers only)"},
    "publish_part_designs":    {"group": "parts", "checked": False, "en": "Publish part designs to the parts library"},
    "approve_part_designs":    {"group": "parts", "checked": False, "en": "Approve part designs into the library"},
    "make_noncritical_parts":  {"group": "parts", "checked": False, "en": "Make non-critical parts by digital manufacturing"},
    "supply_restricted_parts": {"group": "parts", "checked": False, "en": "Supply parts beyond the non-critical list, with quality certificates"},
}

# The five welcome quests. When all are done the member becomes Ambassador
# and the platform opens.
WELCOME_QUESTS = ("profile_complete", "intro_video", "meeting_held", "discord_joined", "consent_answered")
# Quests a person (host, mentor, community team) can mark as done for someone.
CONFIRMABLE_QUESTS = ("meeting_held", "discord_joined", "watched_approval_meeting", "workshop_declared", "quality_certificate")

METRICS = (
    "devices_registered", "faults_resolved", "maintenance_performed", "invites",
    "repairs_and_maintenance", "manuals_added",
    # Counted once their features exist (task board, parts library):
    "verifications", "team_contributions", "designs_accepted", "parts_delivered",
)

TEAMS = ("software", "data", "hardware", "manufacturing", "partnerships", "communications")
MEMBER_STATUSES = ("applicant", "member", "staff", "refused")
PAUSE_AFTER = timedelta(days=183)  # about 6 months


def now() -> datetime:
    return datetime.now(timezone.utc)


# ── Pure rules (unit-tested) ─────────────────────────────────

def is_paused(last_active_at: datetime | None, at: datetime | None = None) -> bool:
    """A member's roles pause after 6 months without activity. No activity
    recorded yet (new or backfilled account) counts as active."""
    if last_active_at is None:
        return False
    at = at or now()
    return at - last_active_at > PAUSE_AFTER


def requirement_status(req: dict, held: set[str], metrics: dict, quests: dict,
                       confirmations: set[str]) -> dict:
    """How far one requirement is: {"met", "done", "needed"}.

    req is {"kind", "ref", "threshold"}. held is the set of active role keys,
    metrics the counts, quests {quest_key: count}, confirmations the role keys
    whose holders have confirmed this member for the role being checked.
    """
    kind, ref = req["kind"], req["ref"]
    needed = req.get("threshold") or 1
    if kind == "role":
        done = 1 if ref in held else 0
    elif kind == "metric":
        done = int(metrics.get(ref, 0))
    elif kind == "quest":
        done = int(quests.get(ref, 0))
    elif kind == "confirmation":
        done = 1 if ref in confirmations else 0
    else:
        done = 0
    return {"met": done >= needed, "done": min(done, needed), "needed": needed}


def quests_done(quests: dict) -> list[str]:
    return [q for q in WELCOME_QUESTS if quests.get(q, 0) >= 1]


def next_status(current: str, join_path: str, quests: dict) -> str:
    """What member_status should be, given the quests done.

    applicant → member when every welcome quest is done. Clinic staff invited
    by a clinic only need the video to get in (status staff); they become
    members like everyone else once the other quests are done too. A refused
    or already-member account never moves back."""
    if current in ("member", "refused"):
        return current
    if len(quests_done(quests)) == len(WELCOME_QUESTS):
        return "member"
    if join_path == "clinic_staff" and quests.get("intro_video", 0) >= 1:
        return "staff"
    return current


def localized(value: dict | None, lang: str) -> str:
    value = value or {}
    return value.get(lang) or value.get("en") or ""


# ── Reading state ────────────────────────────────────────────

async def metrics_for(db: AsyncSession, profile_id) -> dict:
    """Every count a requirement can use. The four activity counts are the
    same SQL the Network directory sorts by (routers/profile.py)."""
    from routers.profile import _counts_for
    counts = await _counts_for(db, profile_id)
    manuals = await db.scalar(
        select(func.count()).select_from(Document).where(Document.uploaded_by == profile_id)
    ) or 0
    out = {m: 0 for m in METRICS}
    out.update(counts)
    out["repairs_and_maintenance"] = counts["faults_resolved"] + counts["maintenance_performed"]
    out["manuals_added"] = int(manuals)
    return out


def profile_is_complete(profile: Profile) -> bool:
    return all((
        profile.avatar_key, (profile.country or "").strip(), (profile.city or "").strip(),
        (profile.country_trained or "").strip(), (profile.why_bme or "").strip(),
    ))


async def quests_for(db: AsyncSession, profile: Profile, user: User | None = None) -> dict:
    """{quest_key: count}. Computed from existing data where possible,
    otherwise read from member_quests."""
    rows = (await db.execute(
        select(MemberQuest.quest_key, MemberQuest.count).where(MemberQuest.profile_id == profile.id)
    )).all()
    quests = {k: int(c or 0) for k, c in rows}
    if user is None:
        user = await db.get(User, profile.id)
    if profile_is_complete(profile):
        quests["profile_complete"] = 1
    if user is not None and user.discord_user_id:
        quests["discord_joined"] = max(1, quests.get("discord_joined", 0))
    if profile.social_consent is not None:
        quests["consent_answered"] = 1
    return quests


async def active_roles(db: AsyncSession, profile_id) -> list[MemberRole]:
    return list((await db.execute(
        select(MemberRole)
        .where(MemberRole.profile_id == profile_id, MemberRole.status == "active")
        .order_by(MemberRole.granted_at)
    )).scalars().all())


async def load_catalogue(db: AsyncSession, include_inactive: bool = False) -> list[dict]:
    q = select(CommunityRole).order_by(CommunityRole.tier, CommunityRole.path, CommunityRole.sort)
    if not include_inactive:
        q = q.where(CommunityRole.active.is_(True))
    roles = (await db.execute(q)).scalars().all()
    reqs = (await db.execute(select(CommunityRoleRequirement))).scalars().all()
    perms = (await db.execute(select(CommunityRolePermission))).scalars().all()
    by_role_req: dict[str, list] = {}
    for r in reqs:
        by_role_req.setdefault(r.role_key, []).append(
            {"kind": r.kind, "ref": r.ref, "threshold": r.threshold})
    by_role_perm: dict[str, list] = {}
    for p in perms:
        by_role_perm.setdefault(p.role_key, []).append(p.permission)
    order = {"role": 0, "quest": 1, "metric": 2, "confirmation": 3}
    return [
        {
            "key": r.key, "path": r.path, "tier": r.tier, "scope": r.scope,
            "unlock": r.unlock, "sort": r.sort, "active": r.active,
            "names": r.names or {}, "descriptions": r.descriptions or {},
            "linkedin_titles": r.linkedin_titles or {},
            "requirements": sorted(by_role_req.get(r.key, []), key=lambda x: (order.get(x["kind"], 9), x["ref"])),
            "permissions": sorted(by_role_perm.get(r.key, [])),
        }
        for r in roles
    ]


async def confirmations_for(db: AsyncSession, profile_id) -> dict[str, set[str]]:
    """{role_key: {confirming role keys}} from member_quests rows named
    confirm:<role_key>:<by_role>. Phase 3 adds the confirm buttons; until then
    admins assign confirmed roles directly."""
    rows = (await db.execute(
        select(MemberQuest.quest_key).where(
            MemberQuest.profile_id == profile_id, MemberQuest.quest_key.like("confirm:%"))
    )).scalars().all()
    out: dict[str, set[str]] = {}
    for key in rows:
        parts = key.split(":")
        if len(parts) == 3:
            out.setdefault(parts[1], set()).add(parts[2])
    return out


async def progress(db: AsyncSession, profile: Profile, user: User | None = None,
                   catalogue: list[dict] | None = None) -> dict:
    """Everything the journey page needs: held roles, quests, metrics and,
    for every role, how far each requirement is."""
    catalogue = catalogue if catalogue is not None else await load_catalogue(db)
    roles = await active_roles(db, profile.id)
    held = {r.role_key for r in roles}
    metrics = await metrics_for(db, profile.id)
    quests = await quests_for(db, profile, user)
    confirmations = await confirmations_for(db, profile.id)
    per_role = {}
    for role in catalogue:
        reqs = [
            {**req, **requirement_status(req, held, metrics, quests, confirmations.get(role["key"], set()))}
            for req in role["requirements"]
        ]
        done = sum(1 for r in reqs if r["met"])
        per_role[role["key"]] = {
            "held": role["key"] in held,
            "requirements": reqs,
            "met": done,
            "total": len(reqs),
            "ready": bool(reqs) and done == len(reqs),
        }
    return {
        "held": held, "roles": roles, "metrics": metrics, "quests": quests,
        "per_role": per_role, "paused": is_paused(profile.last_active_at),
    }


# ── Changing state ───────────────────────────────────────────

async def log_change(db: AsyncSession, actor_id, action: str, target: str | None,
                     before: dict | None = None, after: dict | None = None,
                     reason: str | None = None) -> None:
    db.add(CommunityRoleChange(
        actor_id=actor_id, action=action, target=target,
        before=before, after=after, reason=reason,
    ))


async def grant_role(db: AsyncSession, profile: Profile, role_key: str, source: str,
                     granted_by=None, country: str | None = None, team: str | None = None,
                     reason: str | None = None) -> MemberRole | None:
    """Give a role. Idempotent: an active holding is returned as is, a removed
    one is reactivated. Returns None when the role doesn't exist."""
    role = await db.get(CommunityRole, role_key)
    if role is None:
        return None
    if role.scope == "local":
        country = (country or profile.country or "").strip() or None
        team = None
    elif role.scope == "global":
        country = None
    else:
        country, team = None, None
    existing = await db.scalar(
        select(MemberRole).where(
            MemberRole.profile_id == profile.id,
            MemberRole.role_key == role_key,
            func.coalesce(MemberRole.country, "") == (country or ""),
            func.coalesce(MemberRole.team, "") == (team or ""),
        )
    )
    if existing and existing.status == "active":
        return existing
    if existing:
        existing.status = "active"
        existing.removed_at = None
        existing.removed_reason = None
        existing.source = source
        existing.granted_by = granted_by
        existing.granted_at = now()
        holding = existing
    else:
        holding = MemberRole(
            profile_id=profile.id, role_key=role_key, country=country, team=team,
            source=source, granted_by=granted_by, granted_at=now(),
        )
        db.add(holding)
    await db.flush()
    await log_change(db, granted_by, "role_granted", str(profile.id),
                     after={"role": role_key, "country": country, "team": team, "source": source},
                     reason=reason)
    return holding


async def remove_role(db: AsyncSession, holding: MemberRole, actor_id, reason: str) -> None:
    before = {"role": holding.role_key, "country": holding.country, "team": holding.team}
    holding.status = "removed"
    holding.removed_at = now()
    holding.removed_reason = reason
    await log_change(db, actor_id, "role_removed", str(holding.profile_id), before=before, reason=reason)


async def set_quest(db: AsyncSession, profile_id, quest_key: str, count: int = 1,
                    confirmed_by=None) -> None:
    row = await db.get(MemberQuest, (profile_id, quest_key))
    if row is None:
        db.add(MemberQuest(profile_id=profile_id, quest_key=quest_key, count=count,
                           confirmed_by=confirmed_by, updated_at=now()))
    else:
        row.count = max(row.count or 0, count)
        if confirmed_by is not None:
            row.confirmed_by = confirmed_by
        row.updated_at = now()
    await db.flush()


async def refresh_status(db: AsyncSession, profile: Profile, user: User | None = None,
                         actor_id=None) -> str | None:
    """Move member_status forward when the quests allow it. On becoming a
    member, grant Ambassador. Returns the new status when it changed."""
    quests = await quests_for(db, profile, user)
    new = next_status(profile.member_status, profile.join_path, quests)
    if new == profile.member_status:
        return None
    old = profile.member_status
    profile.member_status = new
    if new == "member":
        profile.member_since = profile.member_since or now()
        await grant_role(db, profile, "ambassador", source="auto", granted_by=actor_id,
                         reason="Welcome quests done")
        app = await db.get(CommunityApplication, profile.id)
        if app and app.status not in ("refused", "withdrawn"):
            app.status = "met"
    await log_change(db, actor_id, "member_status", str(profile.id),
                     before={"member_status": old}, after={"member_status": new})
    await db.flush()
    return new


async def check_unlocks(db: AsyncSession, profile: Profile, user: User | None = None) -> list[str]:
    """Grant every `auto` role whose requirements are all met. Returns the new
    keys. Ambassador is handled by refresh_status. Phase 2 calls this after
    each counting action; phase 1 runs it when the journey page loads."""
    if profile.member_status != "member":
        return []
    prog = await progress(db, profile, user)
    catalogue = await load_catalogue(db)
    new = []
    for role in catalogue:
        if role["unlock"] != "auto" or role["key"] == "ambassador":
            continue
        state = prog["per_role"][role["key"]]
        if state["ready"] and not state["held"]:
            await grant_role(db, profile, role["key"], source="auto", reason="Requirements met")
            new.append(role["key"])
    return new


async def claim_role(db: AsyncSession, profile: Profile, role_key: str,
                     team: str | None = None, user: User | None = None) -> MemberRole:
    """A member takes a `claim` role whose requirements are met."""
    role = await db.get(CommunityRole, role_key)
    if role is None or not role.active:
        raise HTTPException(status_code=404, detail="role_not_found")
    if role.unlock != "claim":
        raise HTTPException(status_code=400, detail="role_not_claimable")
    if profile.member_status != "member":
        raise HTTPException(status_code=403, detail="community_access_pending")
    if role.scope == "global" and team not in TEAMS:
        raise HTTPException(status_code=400, detail="team_required")
    prog = await progress(db, profile, user)
    if not prog["per_role"][role_key]["ready"]:
        raise HTTPException(status_code=400, detail="requirements_not_met")
    return await grant_role(db, profile, role_key, source="claim", granted_by=profile.id, team=team,
                            reason="Claimed")


async def touch_activity(db: AsyncSession, profile_id) -> None:
    """Record activity at most once a day (used to pause roles after 6 months)."""
    cutoff = now() - timedelta(days=1)
    await db.execute(
        update(Profile)
        .where(Profile.id == profile_id,
               (Profile.last_active_at.is_(None)) | (Profile.last_active_at < cutoff))
        .values(last_active_at=now())
    )


# ── Permissions ──────────────────────────────────────────────

class Scope:
    """Where a permission applies: everywhere, or in some countries/teams."""
    def __init__(self):
        self.everywhere = False
        self.countries: set[str] = set()
        self.teams: set[str] = set()

    def __bool__(self):
        return self.everywhere or bool(self.countries) or bool(self.teams)

    def covers(self, country: str | None = None, teams: set[str] | None = None) -> bool:
        if self.everywhere:
            return True
        if country and country in self.countries:
            return True
        return bool(teams and (teams & self.teams))

    def as_dict(self) -> dict:
        return {"everywhere": self.everywhere, "countries": sorted(self.countries), "teams": sorted(self.teams)}


async def permission_scopes(db: AsyncSession, profile: Profile, user: User | None = None) -> dict[str, Scope]:
    """{permission: Scope} for this member. Superusers (the community team
    admins for now) hold every permission everywhere. Paused roles grant
    nothing until the member is active again."""
    if user is None:
        user = await db.get(User, profile.id)
    scopes: dict[str, Scope] = {}
    if user is not None and user.is_superuser:
        for key in PERMISSIONS:
            s = Scope(); s.everywhere = True
            scopes[key] = s
        return scopes
    if profile.member_status != "member" or is_paused(profile.last_active_at):
        return scopes
    rows = (await db.execute(
        select(MemberRole.country, MemberRole.team, CommunityRole.scope, CommunityRolePermission.permission)
        .join(CommunityRole, CommunityRole.key == MemberRole.role_key)
        .join(CommunityRolePermission, CommunityRolePermission.role_key == MemberRole.role_key)
        .where(MemberRole.profile_id == profile.id, MemberRole.status == "active",
               CommunityRole.active.is_(True))
    )).all()
    for country, team, role_scope, perm in rows:
        s = scopes.setdefault(perm, Scope())
        if role_scope == "none":
            s.everywhere = True
        elif role_scope == "global":
            if team:
                s.teams.add(team)
        elif country:
            s.countries.add(country)
    return {k: v for k, v in scopes.items() if v}


async def has_permission(db: AsyncSession, profile: Profile, permission: str,
                         country: str | None = None) -> bool:
    scope = (await permission_scopes(db, profile)).get(permission)
    if not scope:
        return False
    return True if country is None else scope.covers(country=country)


def require_permission(permission: str):
    """FastAPI dependency: the caller's Profile and the Scope of the
    permission, or 403. Usage:

        ctx = Depends(require_permission("view_members"))
        profile, scope = ctx
    """
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission key: {permission}")

    async def dependency(user: User = Depends(current_active_user),
                         db: AsyncSession = Depends(get_db)):
        profile = await db.get(Profile, user.id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        scope = (await permission_scopes(db, profile, user)).get(permission)
        if not scope:
            raise HTTPException(status_code=403, detail="missing_permission")
        return profile, scope

    return dependency
