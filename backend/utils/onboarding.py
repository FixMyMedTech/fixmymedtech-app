# utils/onboarding.py — engineer quests and who may register devices where
#
# Spec: "Engineer and clinic onboarding flow" (2026-11-12), migration 029.
#
# An engineer starts as an applicant with three welcome quests:
#   complete_profile  name, country, city and a short bio filled in (read
#                     from the profile, nothing stored)
#   profile_photo     an avatar exists (read from the profile)
#   community_talk    attended a community talk; a host confirms it after the
#                     call (onboarding_quests row, confirmed_by = the host)
# When all three are done the profile becomes active, permanently: removing
# the photo later does not lock anyone out again.
#
# Device registration for a clinic is allowed for
#   (a) the clinic's own admins, and
#   (b) its confirmed responsible engineers who are members, once the clinic
#       is active (a clinic that signed up without an invitation waits for its
#       clinic talk to be confirmed by the talk host).
# Superusers are treated as members everywhere.

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    OnboardingQuest, Organization, OrgUser, Profile, ResponsibleEngineer, User,
)

QUESTS = ("complete_profile", "profile_photo", "community_talk")
TALK_QUEST = "community_talk"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def can_host_talks(user: User | None) -> bool:
    """Who may confirm a community talk or unlock a clinic after its clinic
    talk. A superuser for now; a Clinics Connector role can join this later."""
    return bool(user and user.is_superuser)


def profile_complete(p: Profile) -> bool:
    return not missing_profile_fields(p)


PROFILE_FIELDS = ("full_name", "country", "city", "bio")


def missing_profile_fields(p: Profile) -> list[str]:
    return [f for f in PROFILE_FIELDS if not (getattr(p, f) or "").strip()]


def is_unlocked(profile: Profile, user: User | None = None) -> bool:
    """Welcome quests done: onboarding_status 'active' (clinic accounts are
    created active, they have no quests). 'staff' accounts (clinic staff added
    by an organization admin) are not gated but do not count as unlocked."""
    if user is not None and user.is_superuser:
        return True
    return profile.onboarding_status == "active"


async def quest_state(db: AsyncSession, profile: Profile) -> dict:
    """{quest_key: {"done": bool, ...}} for the three welcome quests."""
    talk = await db.scalar(
        select(OnboardingQuest).where(
            OnboardingQuest.profile_id == profile.id,
            OnboardingQuest.quest_key == TALK_QUEST,
        )
    )
    return {
        "complete_profile": {
            "done": profile_complete(profile),
            "missing": missing_profile_fields(profile),
        },
        "profile_photo": {"done": bool(profile.avatar_key)},
        "community_talk": {
            "done": talk is not None,
            "confirmed_at": talk.updated_at.isoformat() if talk and talk.updated_at else None,
        },
    }


async def refresh_onboarding_status(db: AsyncSession, profile: Profile) -> bool:
    """Promote an applicant engineer whose three quests are done. Returns True
    when it happened (the caller commits)."""
    if profile.onboarding_status != "applicant" or profile.account_kind != "engineer":
        return False
    state = await quest_state(db, profile)
    if all(q["done"] for q in state.values()):
        profile.onboarding_status = "active"
        profile.active_since = now_utc()
        return True
    return False


async def confirm_talk(db: AsyncSession, profile: Profile, host_id) -> bool:
    """Record the community talk as attended. Idempotent."""
    row = await db.scalar(
        select(OnboardingQuest).where(
            OnboardingQuest.profile_id == profile.id,
            OnboardingQuest.quest_key == TALK_QUEST,
        )
    )
    if row is None:
        db.add(OnboardingQuest(profile_id=profile.id, quest_key=TALK_QUEST,
                           confirmed_by=host_id, updated_at=now_utc()))
        await db.flush()
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

    reason is 'admin' or 'responsible' when allowed, otherwise one of
    LOCK_REASONS."""
    if await _org_role(db, profile.id, org_id) == "admin":
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
    status = await db.scalar(select(Organization.clinic_status).where(Organization.id == org_id))
    if status == "talk_pending":
        return False, "clinic_talk_pending"
    return True, "responsible"


async def registrable_clinics(db: AsyncSession, profile: Profile,
                              user: User | None = None) -> dict:
    """Clinics this profile may register devices for, and the ones where it is
    named but still locked (with the reason), for the Register-device page."""
    unlocked, locked = [], []
    admin_rows = (await db.execute(
        select(Organization.id, Organization.name)
        .join(OrgUser, OrgUser.organization_id == Organization.id)
        .where(OrgUser.profile_id == profile.id, OrgUser.role == "admin")
        .order_by(Organization.name)
    )).all()
    seen = set()
    for oid, name in admin_rows:
        seen.add(oid)
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
    if engineer.onboarding_status != "active":
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
