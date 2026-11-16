# utils/onboarding.py — who may register devices where, and who hosts talks
#
# Spec: "Engineer and clinic onboarding flow" (2026-11-12), migration 030.
#
# The welcome quests themselves live in utils/community.py (three quests:
# complete profile, add a photo, attend a community talk). When they are done
# profiles.member_status becomes 'member', permanently: removing the photo
# later does not lock anyone out again. The app calls that "Contributor".
#
# Device registration for a clinic is allowed for
#   (a) the clinic's own admins, and
#   (b) its confirmed responsible engineers whose quests are done,
# and in both cases only once the clinic is active: a clinic created without
# an invitation waits for its clinic talk to be confirmed by a talk host
# (decision 2026-11-13). Superusers count as members everywhere.

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Organization, OrgUser, Profile, ResponsibleEngineer, TeamMember, User,
)
from utils import community as cm

# The same three quests as cm.WELCOME_QUESTS, under the names the onboarding
# pages use (quest_state below).
QUESTS = ("complete_profile", "profile_photo", "community_talk")
TALK_QUEST = cm.TALK_QUEST
# The team whose members unlock clinics after the clinic talk.
CLINIC_TEAM = "clinics_connector"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def can_host_talks(db: AsyncSession, user: User | None, profile: Profile | None = None) -> bool:
    """Who may confirm a community talk: superusers and Community Builders
    (the same people who welcome applicants, utils/community.py)."""
    if user is None:
        return False
    if user.is_superuser:
        return True
    profile = profile or await db.get(Profile, user.id)
    if profile is None:
        return False
    return (await cm.powers_for(db, profile, user)).confirm_quests


async def can_unlock_clinics(db: AsyncSession, user: User | None, profile: Profile | None = None) -> bool:
    """Who may unlock a clinic after its clinic talk: superusers and members
    or leads of the Clinics Connector team (decision 2026-11-12)."""
    if user is None:
        return False
    if user.is_superuser:
        return True
    profile = profile or await db.get(Profile, user.id)
    if profile is None or profile.member_status != "member" or cm.is_paused(profile.last_active_at):
        return False
    level = await db.scalar(select(TeamMember.level).where(
        TeamMember.profile_id == profile.id, TeamMember.team_key == CLINIC_TEAM,
        TeamMember.status == "active"))
    return level in ("member", "lead")


async def is_host(db: AsyncSession, user: User | None, profile: Profile | None = None) -> bool:
    """Shows the /host page: either power."""
    return (await can_host_talks(db, user, profile)) or (await can_unlock_clinics(db, user, profile))


def missing_profile_fields(p: Profile) -> list[str]:
    return cm.missing_profile_fields(p)


def profile_complete(p: Profile) -> bool:
    return cm.profile_is_complete(p)


def is_unlocked(profile: Profile, user: User | None = None) -> bool:
    """Welcome quests done: member_status 'member'. Staff (clinic accounts and
    clinic staff) pass the platform gate but do not count as unlocked
    engineers."""
    if user is not None and user.is_superuser:
        return True
    return profile.member_status == "member"


async def quest_state(db: AsyncSession, profile: Profile) -> dict:
    """{quest_key: {"done": bool, ...}} for the three welcome quests."""
    quests = await cm.quests_for(db, profile)
    return {
        "complete_profile": {
            "done": bool(quests.get("profile_complete")),
            "missing": cm.missing_profile_fields(profile),
        },
        "profile_photo": {"done": bool(quests.get("profile_photo"))},
        "community_talk": {"done": bool(quests.get(TALK_QUEST))},
    }


async def refresh_onboarding_status(db: AsyncSession, profile: Profile) -> bool:
    """Promote an applicant whose three quests are done. Returns True when it
    happened (the caller commits)."""
    if profile.member_status != "applicant" or profile.account_kind != "engineer":
        return False
    return (await cm.refresh_status(db, profile)) == "member"


async def confirm_talk(db: AsyncSession, profile: Profile, host_id) -> bool:
    """Record the community talk as attended. Idempotent."""
    await cm.set_quest(db, profile.id, TALK_QUEST, confirmed_by=host_id)
    await cm.log_change(db, host_id, "quest_confirmed", str(profile.id), after={"quest": TALK_QUEST})
    return await refresh_onboarding_status(db, profile)


# ── Device registration ─────────────────────────────────────────────────────

LOCK_REASONS = ("quests_pending", "not_now", "clinic_talk_pending", "not_named")


async def _org_role(db: AsyncSession, profile_id, org_id) -> str | None:
    return await db.scalar(
        select(OrgUser.role).where(
            OrgUser.profile_id == profile_id,
            OrgUser.organization_id == org_id,
        )
    )


async def registration_check(db: AsyncSession, profile: Profile, org_id,
                             user: User | None = None) -> tuple[bool, str]:
    """May this profile register a device for this clinic? (allowed, reason)

    reason is 'admin', 'responsible' or 'superuser' when allowed, otherwise
    one of LOCK_REASONS. A clinic waiting for its talk is locked for everyone,
    its admins included (decision 2026-11-13)."""
    if user is not None and user.is_superuser:
        return True, "superuser"
    status = await db.scalar(select(Organization.clinic_status).where(Organization.id == org_id))
    if await _org_role(db, profile.id, org_id) == "admin":
        if status == "talk_pending":
            return False, "clinic_talk_pending"
        return True, "admin"
    row = await db.scalar(
        select(ResponsibleEngineer).where(
            ResponsibleEngineer.organization_id == org_id,
            ResponsibleEngineer.engineer_id == profile.id,
        )
    )
    if row is None:
        return False, "not_named"
    if row.status != "confirmed":
        return False, "not_now"
    if not is_unlocked(profile, user):
        return False, "quests_pending"
    if status == "talk_pending":
        return False, "clinic_talk_pending"
    return True, "responsible"


async def registrable_clinics(db: AsyncSession, profile: Profile,
                              user: User | None = None) -> dict:
    """Clinics this profile may register devices for, and the ones where it is
    named but still locked (with the reason), for the Register-device page."""
    unlocked, locked = [], []
    admin_rows = (await db.execute(
        select(Organization.id, Organization.name, Organization.clinic_status)
        .join(OrgUser, OrgUser.organization_id == Organization.id)
        .where(OrgUser.profile_id == profile.id, OrgUser.role == "admin")
        .order_by(Organization.name)
    )).all()
    superuser = bool(user is not None and user.is_superuser)
    seen = set()
    for oid, name, clinic_status in admin_rows:
        seen.add(oid)
        if clinic_status == "talk_pending" and not superuser:
            locked.append({"id": str(oid), "name": name, "reason": "clinic_talk_pending"})
        else:
            unlocked.append({"id": str(oid), "name": name, "via": "admin"})

    rows = (await db.execute(
        select(ResponsibleEngineer, Organization.name, Organization.clinic_status)
        .join(Organization, Organization.id == ResponsibleEngineer.organization_id)
        .where(ResponsibleEngineer.engineer_id == profile.id)
        .order_by(Organization.name)
    )).all()
    unlocked_user = is_unlocked(profile, user)
    for row, name, clinic_status in rows:
        if row.organization_id in seen:
            continue
        if row.status != "confirmed":
            reason = "not_now"
        elif not unlocked_user:
            reason = "quests_pending"
        elif clinic_status == "talk_pending":
            reason = "clinic_talk_pending"
        else:
            reason = None
        entry = {"id": str(row.organization_id), "name": name}
        if reason:
            locked.append({**entry, "reason": reason})
        else:
            unlocked.append({**entry, "via": "responsible"})
    return {"unlocked": unlocked, "locked": locked, "is_unlocked": unlocked_user}


async def responsible_org_ids(db: AsyncSession, profile: Profile,
                              user: User | None = None) -> list:
    """Clinics whose private device pages this profile sees as a responsible
    engineer: confirmed, quests done, clinic active."""
    if not is_unlocked(profile, user):
        return []
    return list((await db.execute(
        select(ResponsibleEngineer.organization_id)
        .join(Organization, Organization.id == ResponsibleEngineer.organization_id)
        .where(
            ResponsibleEngineer.engineer_id == profile.id,
            ResponsibleEngineer.status == "confirmed",
            Organization.clinic_status == "active",
        )
    )).scalars().all())


async def engineer_status(db: AsyncSession, row: ResponsibleEngineer,
                          engineer: Profile, clinic_status: str) -> str:
    """One word for the Engineers tab: can_register, waiting_quests,
    waiting_talk (the clinic's own talk) or not_now."""
    if row.status != "confirmed":
        return "not_now"
    if engineer.member_status != "member":
        superuser = await db.scalar(select(User.is_superuser).where(User.id == engineer.id))
        if not superuser:
            return "waiting_quests"
    if clinic_status == "talk_pending":
        return "waiting_talk"
    return "can_register"


async def admin_count(db: AsyncSession, org_id) -> int:
    return await db.scalar(
        select(func.count()).select_from(OrgUser).where(
            OrgUser.organization_id == org_id, OrgUser.role == "admin",
        )
    ) or 0
