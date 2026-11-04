# utils/community.py — the community journey rules: teams, achievements, welcome quests
#
# Community teams (Communicator, Community Builder, Clinics Connector) are not
# org roles. org_users.role decides what someone can do inside one
# organization; a team place is what a member does for the community. Each
# place has a level: candidate, member or lead.
#
# Achievements (Mapper, Ambassador, Supporter…) belong to one team's category
# and have 10 star levels. Mapper is counted by the platform; the others are
# recognised by members of their team. Guide: docs/docs/community-guide.md
#
# Who can do what is decided in code (powers_from), from the caller's team
# places. Pure helpers have no database access, so the rules are unit-tested
# in backend/tests/test_community.py.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.users import current_active_user
from models.models import (
    User, Profile, Document,
    CommunityTeam, TeamMember, Achievement, AchievementRecord,
    MemberQuest, CommunityApplication, CommunityChange,
)

# The five welcome quests. When all are done the applicant becomes a member
# and the platform opens.
WELCOME_QUESTS = ("profile_complete", "intro_video", "meeting_held", "discord_joined", "consent_answered")
# Quests a Community Builder can mark as done for someone.
CONFIRMABLE_QUESTS = ("meeting_held", "discord_joined")

METRICS = ("devices_registered", "faults_resolved", "maintenance_performed", "invites", "manuals_added")
LEVELS = ("candidate", "member", "lead")
MEMBER_STATUSES = ("applicant", "member", "staff", "refused")
STAR_LEVELS = 10
PAUSE_AFTER = timedelta(days=183)  # about 6 months

# The team whose members welcome applicants (and can make anyone a candidate).
WELCOMING_TEAM = "community_builder"


def now() -> datetime:
    return datetime.now(timezone.utc)


# ── Pure rules (unit-tested) ─────────────────────────────────

def is_paused(last_active_at: datetime | None, at: datetime | None = None) -> bool:
    """Team powers pause after 6 months without activity. No activity
    recorded yet (new or backfilled account) counts as active."""
    if last_active_at is None:
        return False
    at = at or now()
    return at - last_active_at > PAUSE_AFTER


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


def star_level(count: int, thresholds: list[int]) -> dict:
    """{"level": 0-10, "count", "next": count needed for the next star or None}."""
    level = sum(1 for t in thresholds if count >= t)
    nxt = thresholds[level] if level < len(thresholds) else None
    prev = thresholds[level - 1] if level > 0 else 0
    return {"level": level, "count": count, "next": nxt, "prev": prev}


def localized(value: dict | None, lang: str) -> str:
    value = value or {}
    return value.get(lang) or value.get("en") or ""


@dataclass
class Powers:
    """What the caller can do in the community. Built by powers_from."""
    superuser: bool = False
    view_applicants: bool = False
    decide_applicants: bool = False
    confirm_quests: bool = False
    view_members: bool = False
    view_history: bool = False
    name_leads: bool = False
    set_candidate: set = field(default_factory=set)    # teams where they can add candidates
    manage_members: set = field(default_factory=set)   # teams where they add/remove members
    edit_team: set = field(default_factory=set)        # teams whose texts they edit
    recognise: set = field(default_factory=set)        # achievement categories they record

    def can_add(self, team: str, level: str) -> bool:
        if level == "lead":
            return self.name_leads
        if level == "member":
            return team in self.manage_members
        return team in self.set_candidate or team in self.manage_members

    def can_remove(self, team: str, level: str) -> bool:
        return self.can_add(team, level)

    def as_list(self) -> list[str]:
        """Flat keys for the frontend (sidebar, buttons)."""
        out = [k for k in ("view_applicants", "decide_applicants", "confirm_quests",
                           "view_members", "view_history", "name_leads") if getattr(self, k)]
        for name in ("set_candidate", "manage_members", "edit_team", "recognise"):
            out += [f"{name}:{t}" for t in sorted(getattr(self, name))]
        return out


def powers_from(superuser: bool, member_status: str, paused: bool, places: dict[str, str],
                all_teams: tuple | list = ()) -> Powers:
    """places is {team_key: level} for the caller's active places.

    - Superusers can do everything.
    - Candidates have no powers; paused or non-member accounts neither.
    - A team member (or lead) recognises achievements of their team's
      category and sees the members list.
    - Community Builders also welcome applicants (review, host the call,
      confirm Discord) and can make anyone a candidate for any team.
    - A lead adds and removes members of their own team, edits its texts and
      sees the history. Only superusers name leads.
    """
    p = Powers()
    teams = set(all_teams) | set(places)
    if superuser:
        p.superuser = True
        p.view_applicants = p.decide_applicants = p.confirm_quests = True
        p.view_members = p.view_history = p.name_leads = True
        p.set_candidate = set(teams)
        p.manage_members = set(teams)
        p.edit_team = set(teams)
        p.recognise = set(teams)
        return p
    if member_status != "member" or paused:
        return p
    for team, level in places.items():
        if level not in ("member", "lead"):
            continue
        p.view_members = True
        p.recognise.add(team)
        if team == WELCOMING_TEAM:
            p.view_applicants = p.decide_applicants = p.confirm_quests = True
            p.set_candidate |= teams
        if level == "lead":
            p.view_history = True
            p.manage_members.add(team)
            p.edit_team.add(team)
            p.set_candidate.add(team)
    return p


# ── Reading state ────────────────────────────────────────────

async def metrics_for(db: AsyncSession, profile_id) -> dict:
    """Activity counts. The first four are the same SQL the Network directory
    sorts by (routers/profile.py)."""
    from routers.profile import _counts_for
    counts = await _counts_for(db, profile_id)
    manuals = await db.scalar(
        select(func.count()).select_from(Document).where(Document.uploaded_by == profile_id)
    ) or 0
    out = {m: 0 for m in METRICS}
    out.update({k: int(v) for k, v in counts.items()})
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


async def load_teams(db: AsyncSession, include_inactive: bool = False) -> list[dict]:
    q = select(CommunityTeam).order_by(CommunityTeam.sort, CommunityTeam.key)
    if not include_inactive:
        q = q.where(CommunityTeam.active.is_(True))
    return [team_out(t) for t in (await db.execute(q)).scalars().all()]


def team_out(t: CommunityTeam) -> dict:
    return {"key": t.key, "sort": t.sort, "names": t.names or {}, "descriptions": t.descriptions or {},
            "tasks": t.tasks or {}, "linkedin_titles": t.linkedin_titles or {}, "active": t.active}


async def load_achievements(db: AsyncSession, include_inactive: bool = False) -> list[dict]:
    q = select(Achievement).order_by(Achievement.sort, Achievement.key)
    if not include_inactive:
        q = q.where(Achievement.active.is_(True))
    return [
        {"key": a.key, "team_key": a.team_key, "source": a.source, "metric": a.metric,
         "levels": list(a.levels or []), "sort": a.sort, "names": a.names or {},
         "descriptions": a.descriptions or {}, "active": a.active}
        for a in (await db.execute(q)).scalars().all()
    ]


async def team_places(db: AsyncSession, profile_id) -> list[TeamMember]:
    return list((await db.execute(
        select(TeamMember)
        .where(TeamMember.profile_id == profile_id, TeamMember.status == "active")
        .order_by(TeamMember.granted_at)
    )).scalars().all())


async def recognised_counts(db: AsyncSession, profile_id) -> dict[str, int]:
    rows = (await db.execute(
        select(AchievementRecord.achievement_key, func.sum(AchievementRecord.count))
        .where(AchievementRecord.profile_id == profile_id)
        .group_by(AchievementRecord.achievement_key)
    )).all()
    return {k: int(n or 0) for k, n in rows}


async def achievement_progress(db: AsyncSession, profile_id, achievements: list[dict] | None = None,
                               metrics: dict | None = None) -> list[dict]:
    """Every achievement with this member's count and star level."""
    achievements = achievements if achievements is not None else await load_achievements(db)
    metrics = metrics if metrics is not None else await metrics_for(db, profile_id)
    recognised = await recognised_counts(db, profile_id)
    out = []
    for a in achievements:
        count = int(metrics.get(a["metric"], 0)) if a["source"] == "metric" else recognised.get(a["key"], 0)
        out.append({"key": a["key"], "team_key": a["team_key"], **star_level(count, a["levels"])})
    return out


async def powers_for(db: AsyncSession, profile: Profile, user: User | None = None) -> Powers:
    if user is None:
        user = await db.get(User, profile.id)
    places = {m.team_key: m.level for m in await team_places(db, profile.id)}
    all_teams = (await db.execute(select(CommunityTeam.key))).scalars().all()
    return powers_from(bool(user and user.is_superuser), profile.member_status,
                       is_paused(profile.last_active_at), places, all_teams)


# ── Changing state ───────────────────────────────────────────

async def log_change(db: AsyncSession, actor_id, action: str, target: str | None,
                     before: dict | None = None, after: dict | None = None,
                     reason: str | None = None) -> None:
    db.add(CommunityChange(
        actor_id=actor_id, action=action, target=target,
        before=before, after=after, reason=reason,
    ))


async def set_team_place(db: AsyncSession, profile: Profile, team_key: str, level: str,
                         granted_by=None, reason: str | None = None) -> TeamMember:
    """Put someone in a team at a level. An existing active place changes
    level (candidate → member, member → lead…)."""
    existing = await db.scalar(select(TeamMember).where(
        TeamMember.profile_id == profile.id, TeamMember.team_key == team_key,
        TeamMember.status == "active"))
    before = {"team": team_key, "level": existing.level} if existing else None
    if existing and existing.level == level:
        return existing
    if existing:
        existing.level = level
        existing.granted_by = granted_by
        existing.granted_at = now()
        place = existing
    else:
        place = TeamMember(profile_id=profile.id, team_key=team_key, level=level,
                           granted_by=granted_by, granted_at=now())
        db.add(place)
    await db.flush()
    await log_change(db, granted_by, "team_changed" if before else "team_added", str(profile.id),
                     before=before, after={"team": team_key, "level": level}, reason=reason)
    return place


async def remove_team_place(db: AsyncSession, place: TeamMember, actor_id, reason: str) -> None:
    before = {"team": place.team_key, "level": place.level}
    place.status = "removed"
    place.removed_at = now()
    place.removed_reason = reason
    await log_change(db, actor_id, "team_removed", str(place.profile_id), before=before, reason=reason)


async def recognise(db: AsyncSession, profile_id, achievement_key: str, count: int, note: str | None,
                    actor_id) -> AchievementRecord:
    record = AchievementRecord(profile_id=profile_id, achievement_key=achievement_key, count=count,
                               note=note, recognised_by=actor_id, created_at=now())
    db.add(record)
    await db.flush()
    await log_change(db, actor_id, "achievement_recognised", str(profile_id),
                     after={"achievement": achievement_key, "count": count}, reason=note)
    return record


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
    """Move member_status forward when the quests allow it. Returns the new
    status when it changed."""
    quests = await quests_for(db, profile, user)
    new = next_status(profile.member_status, profile.join_path, quests)
    if new == profile.member_status:
        return None
    old = profile.member_status
    profile.member_status = new
    if new == "member":
        profile.member_since = profile.member_since or now()
        app = await db.get(CommunityApplication, profile.id)
        if app and app.status not in ("refused", "withdrawn"):
            app.status = "met"
    await log_change(db, actor_id, "member_status", str(profile.id),
                     before={"member_status": old}, after={"member_status": new})
    await db.flush()
    return new


async def touch_activity(db: AsyncSession, profile_id) -> None:
    """Record activity at most once a day (team powers pause after 6 months)."""
    cutoff = now() - timedelta(days=1)
    await db.execute(
        update(Profile)
        .where(Profile.id == profile_id,
               (Profile.last_active_at.is_(None)) | (Profile.last_active_at < cutoff))
        .values(last_active_at=now())
    )


def require_power(check):
    """FastAPI dependency: (profile, powers) when check(powers) is true, else 403.

        ctx = Depends(require_power(lambda p: p.view_members))
    """
    async def dependency(user: User = Depends(current_active_user),
                         db: AsyncSession = Depends(get_db)):
        profile = await db.get(Profile, user.id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        powers = await powers_for(db, profile, user)
        if not check(powers):
            raise HTTPException(status_code=403, detail="missing_permission")
        return profile, powers

    return dependency
