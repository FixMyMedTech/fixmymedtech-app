# routers/community_work.py — wave 5: claims to validate and the community
# task board (migration 033). Mounted at /api/community next to
# routers/community.py.
#
# Claims
#   GET  /claims/options          recognised achievements a member can claim
#   POST /claims                  claim (achievement, count, note)
#   POST /claims/{id}/proof       add a proof photo (claimant)
#   GET  /claims/{id}/proof       the photo (claimant and validators)
#   GET  /claims/mine             my claims
#   GET  /claims/review           claims I can validate (my teams', not mine)
#   POST /claims/{id}/confirm     lead/superuser: confirmed; member: one vote of two
#   POST /claims/{id}/more        ask for more (note)
#   POST /claims/{id}/decline     decline (note)
# Tasks
#   GET  /tasks                   board: open, mine, to check, done (+ points)
#   POST /tasks                   create (members)
#   POST /tasks/find-manual       "find this manual" (any signed-in user; deduped)
#   POST /tasks/{id}/take | /done | /check | /send-back | /cancel

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File as FileParam, HTTPException, UploadFile
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.storage import get_file, upload_file
from models.models import Achievement, AchievementClaim, CommunityTask, Profile
from utils import community as cm
from utils.serialize import row

router = APIRouter()
signed_in = cm.require_power(lambda p: True)

CONFIRMATIONS_NEEDED = 2          # members, when no lead confirms
TASK_KINDS = ("find_manual", "verify_clinic", "fill_brand_list", "other")
FIND_MANUAL_POINTS = 20


def _now():
    return datetime.now(timezone.utc)


def _is_member(profile: Profile, powers) -> bool:
    return powers.superuser or profile.member_status == "member"


async def _names(db, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = (await db.execute(select(Profile.id, Profile.full_name, Profile.username)
                             .where(Profile.id.in_(ids)))).all()
    return {i: (fn or un or "") for i, fn, un in rows}


# ── claims ────────────────────────────────────────────────────────────────

class ClaimIn(BaseModel):
    achievement_key: str
    count: int = Field(default=1, ge=1, le=100)
    note: str = Field(min_length=3, max_length=2000)


class ReviewIn(BaseModel):
    note: Optional[str] = Field(default=None, max_length=2000)


async def _claimable(db) -> list[Achievement]:
    return (await db.execute(select(Achievement).where(Achievement.active.is_(True),
                                                       Achievement.source == "recognised")
                             .order_by(Achievement.team_key, Achievement.sort))).scalars().all()


def _ach_name(a: Achievement, lang: str = "en") -> str:
    names = a.names or {}
    return names.get(lang) or names.get("en") or a.key


async def _claims_out(db, claims, achs: dict) -> list[dict]:
    names = await _names(db, {c.profile_id for c in claims} | {c.reviewed_by for c in claims}
                         | {i for c in claims for i in (c.confirmed_by or [])})
    out = []
    for c in claims:
        a = achs.get(c.achievement_key)
        d = row(c)
        d.update(
            claimant=names.get(c.profile_id, ""),
            achievement_names=(a.names if a else {}),
            team_key=a.team_key if a else None,
            confirmed_names=[names.get(i, "") for i in (c.confirmed_by or [])],
            reviewer=names.get(c.reviewed_by, ""),
            needed=CONFIRMATIONS_NEEDED,
            has_proof=bool(c.proof_key),
        )
        d["confirmed_by"] = [str(i) for i in (c.confirmed_by or [])]
        out.append(d)
    return out


async def _ach_map(db) -> dict:
    return {a.key: a for a in (await db.execute(select(Achievement))).scalars().all()}


@router.get("/claims/options")
async def claim_options(ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    return [{"key": a.key, "team_key": a.team_key, "names": a.names, "descriptions": a.descriptions}
            for a in await _claimable(db)]


@router.post("/claims")
async def make_claim(body: ClaimIn, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    if not _is_member(profile, powers):
        raise HTTPException(status_code=403, detail="Finish your welcome steps to claim achievements")
    ach = await db.get(Achievement, body.achievement_key)
    if ach is None or not ach.active or ach.source != "recognised":
        raise HTTPException(status_code=400, detail="This achievement counts by itself, no claim needed")
    claim = AchievementClaim(profile_id=profile.id, achievement_key=ach.key, count=body.count,
                             note=body.note.strip(), confirmed_by=[])
    db.add(claim)
    await db.commit()
    return {"id": str(claim.id), "status": claim.status}


@router.post("/claims/{claim_id}/proof")
async def add_proof(claim_id: uuid.UUID, photo: UploadFile = FileParam(...), ctx=Depends(signed_in),
                    db: AsyncSession = Depends(get_db)):
    profile, _p = ctx
    claim = await db.get(AchievementClaim, claim_id)
    if claim is None or claim.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Claim not found")
    content = await photo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty photo")
    name = photo.filename or "proof.jpg"
    claim.proof_key = await upload_file(
        "claims", str(claim.id), name, content, photo.content_type or "application/octet-stream",
        object_id=f"proof_{uuid.uuid4().hex}{os.path.splitext(name)[1].lower() or '.jpg'}")
    if claim.status == "more_info":
        claim.status = "pending"
    await db.commit()
    return {"proof": True}


@router.get("/claims/{claim_id}/proof")
async def get_proof(claim_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    claim = await db.get(AchievementClaim, claim_id)
    if claim is None or not claim.proof_key:
        raise HTTPException(status_code=404, detail="No proof")
    ach = await db.get(Achievement, claim.achievement_key)
    if claim.profile_id != profile.id and not (ach and ach.team_key in powers.recognise):
        raise HTTPException(status_code=403, detail="Not yours to see")
    obj = await get_file(claim.proof_key)
    if not obj:
        raise HTTPException(status_code=404, detail="No proof")
    content, ctype = obj
    return FastAPIResponse(content=content, media_type=ctype)


@router.get("/claims/mine")
async def my_claims(ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, _p = ctx
    claims = (await db.execute(select(AchievementClaim).where(AchievementClaim.profile_id == profile.id)
                               .order_by(AchievementClaim.created_at.desc()).limit(50))).scalars().all()
    return await _claims_out(db, claims, await _ach_map(db))


@router.get("/claims/review")
async def claims_to_review(ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    achs = await _ach_map(db)
    keys = [k for k, a in achs.items() if a.team_key in powers.recognise]
    if not keys:
        return {"claims": [], "can_review": False}
    claims = (await db.execute(
        select(AchievementClaim).where(AchievementClaim.achievement_key.in_(keys),
                                       AchievementClaim.status.in_(("pending", "more_info")),
                                       AchievementClaim.profile_id != profile.id)
        .order_by(AchievementClaim.created_at))).scalars().all()
    out = await _claims_out(db, claims, achs)
    for d in out:
        d["is_lead_here"] = powers.superuser or d["team_key"] in powers.manage_members
        d["i_confirmed"] = str(profile.id) in d["confirmed_by"]
    return {"claims": out, "can_review": True}


async def _review_target(db, claim_id, ctx):
    profile, powers = ctx
    claim = await db.get(AchievementClaim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    ach = await db.get(Achievement, claim.achievement_key)
    if ach is None or ach.team_key not in powers.recognise:
        raise HTTPException(status_code=403, detail="Only this achievement's team can validate it")
    if claim.profile_id == profile.id and not powers.superuser:
        raise HTTPException(status_code=400, detail="Not for your own claim")
    if claim.status not in ("pending", "more_info"):
        raise HTTPException(status_code=409, detail="This claim is already decided")
    return profile, powers, claim, ach


@router.post("/claims/{claim_id}/confirm")
async def confirm_claim(claim_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers, claim, ach = await _review_target(db, claim_id, ctx)
    lead = powers.superuser or ach.team_key in powers.manage_members
    votes = list(claim.confirmed_by or [])
    if profile.id not in votes:
        votes.append(profile.id)
    claim.confirmed_by = votes
    if lead or len(votes) >= CONFIRMATIONS_NEEDED:
        record = await cm.recognise(db, claim.profile_id, ach.key, claim.count,
                                    f"Claim: {claim.note}"[:2000], profile.id)
        claim.status = "confirmed"
        claim.record_id = record.id
        claim.reviewed_by = profile.id
        claim.reviewed_at = _now()
    await db.commit()
    return {"status": claim.status, "confirmations": len(votes), "needed": CONFIRMATIONS_NEEDED}


@router.post("/claims/{claim_id}/more")
async def more_info(claim_id: uuid.UUID, body: ReviewIn, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, _powers, claim, _a = await _review_target(db, claim_id, ctx)
    claim.status = "more_info"
    claim.review_note = (body.note or "").strip() or None
    claim.reviewed_by = profile.id
    claim.reviewed_at = _now()
    await db.commit()
    return {"status": claim.status}


@router.post("/claims/{claim_id}/decline")
async def decline_claim(claim_id: uuid.UUID, body: ReviewIn, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, _powers, claim, _a = await _review_target(db, claim_id, ctx)
    claim.status = "declined"
    claim.review_note = (body.note or "").strip() or None
    claim.reviewed_by = profile.id
    claim.reviewed_at = _now()
    await db.commit()
    return {"status": claim.status}


class ClaimEdit(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


@router.patch("/claims/{claim_id}")
async def answer_more(claim_id: uuid.UUID, body: ClaimEdit, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    """The claimant adds what was asked; the claim goes back to pending."""
    profile, _p = ctx
    claim = await db.get(AchievementClaim, claim_id)
    if claim is None or claim.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status not in ("pending", "more_info"):
        raise HTTPException(status_code=409, detail="This claim is already decided")
    claim.note = body.note.strip()
    claim.status = "pending"
    await db.commit()
    return {"status": claim.status}


# ── task board ────────────────────────────────────────────────────────────

class TaskIn(BaseModel):
    kind: str = "other"
    title: str = Field(min_length=3, max_length=200)
    details: Optional[str] = Field(default=None, max_length=2000)
    points: int = Field(default=10, ge=1, le=500)


class FindManualIn(BaseModel):
    manufacturer: Optional[str] = Field(default=None, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    device_id: Optional[uuid.UUID] = None


class DoneIn(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


def _can_check(task: CommunityTask, profile: Profile, powers) -> bool:
    if task.taken_by == profile.id:
        return False
    return powers.superuser or task.created_by == profile.id or bool(powers.manage_members)


@router.get("/tasks")
async def board(ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    tasks = (await db.execute(select(CommunityTask).where(CommunityTask.status != "cancelled")
                              .order_by(CommunityTask.created_at.desc()).limit(300))).scalars().all()
    names = await _names(db, {t.created_by for t in tasks} | {t.taken_by for t in tasks})

    def out(t):
        d = row(t)
        d.update(creator=names.get(t.created_by, ""), taker=names.get(t.taken_by, ""),
                 mine=t.taken_by == profile.id, can_check=t.status == "review" and _can_check(t, profile, powers),
                 can_cancel=t.status in ("open",) and (t.created_by == profile.id or powers.superuser))
        return d

    pts = (await db.execute(
        select(CommunityTask.taken_by, func.sum(CommunityTask.points))
        .where(CommunityTask.status == "done").group_by(CommunityTask.taken_by)
        .order_by(func.sum(CommunityTask.points).desc()).limit(10))).all()
    leader_names = await _names(db, {p for p, _ in pts})
    my_points = await db.scalar(select(func.coalesce(func.sum(CommunityTask.points), 0)).where(
        CommunityTask.status == "done", CommunityTask.taken_by == profile.id))
    return {
        "open": [out(t) for t in tasks if t.status == "open"],
        "mine": [out(t) for t in tasks if t.taken_by == profile.id and t.status in ("taken", "review")],
        "to_check": [out(t) for t in tasks if t.status == "review" and _can_check(t, profile, powers)],
        "done": [out(t) for t in tasks if t.status == "done"][:20],
        "my_points": int(my_points or 0),
        "leaders": [{"name": leader_names.get(p, ""), "points": int(n)} for p, n in pts],
        "can_create": _is_member(profile, powers),
        "can_take": _is_member(profile, powers),
    }


@router.post("/tasks")
async def create_task(body: TaskIn, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    if not _is_member(profile, powers):
        raise HTTPException(status_code=403, detail="Finish your welcome steps to post tasks")
    if body.kind not in TASK_KINDS:
        raise HTTPException(status_code=400, detail="Unknown kind of task")
    task = CommunityTask(kind=body.kind, title=body.title.strip(), details=(body.details or "").strip() or None,
                         points=body.points, created_by=profile.id)
    db.add(task)
    await db.commit()
    return {"id": str(task.id)}


@router.post("/tasks/find-manual")
async def find_manual(body: FindManualIn, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    """"Can't find it? Create a find-this-manual task" (library, device card).
    One open task per brand + model."""
    profile, _p = ctx
    model = body.model.strip()
    brand = (body.manufacturer or "").strip()
    if brand and model.lower().startswith(brand.lower() + " "):
        model = model[len(brand):].strip()      # "Zoll" + "Zoll X999" → X999
    existing = (await db.execute(select(CommunityTask).where(
        CommunityTask.kind == "find_manual", CommunityTask.status.in_(("open", "taken", "review")),
        func.lower(CommunityTask.ref_model) == model.lower(),
        func.lower(func.coalesce(CommunityTask.ref_manufacturer, "")) == brand.lower(),
    ))).scalars().first()
    if existing:
        return {"id": str(existing.id), "existing": True}
    task = CommunityTask(
        kind="find_manual", title=f"Find the manual: {' '.join(x for x in (brand, model) if x)}",
        details="Upload it to the library or link it from iFixit, the manufacturer or a distributor.",
        points=FIND_MANUAL_POINTS, ref_manufacturer=brand or None, ref_model=model,
        ref_device_id=body.device_id, created_by=profile.id)
    db.add(task)
    await db.commit()
    return {"id": str(task.id), "existing": False}


async def _task(db, task_id) -> CommunityTask:
    task = await db.get(CommunityTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/take")
async def take(task_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    if not _is_member(profile, powers):
        raise HTTPException(status_code=403, detail="Finish your welcome steps to take tasks")
    task = await _task(db, task_id)
    if task.status != "open":
        raise HTTPException(status_code=409, detail="Someone already took this task")
    task.status, task.taken_by, task.taken_at = "taken", profile.id, _now()
    await db.commit()
    return {"status": task.status}


@router.post("/tasks/{task_id}/done")
async def done(task_id: uuid.UUID, body: DoneIn, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, _p = ctx
    task = await _task(db, task_id)
    if task.taken_by != profile.id or task.status != "taken":
        raise HTTPException(status_code=409, detail="Only who took the task can mark it done")
    task.status, task.done_note, task.done_at = "review", body.note.strip(), _now()
    await db.commit()
    return {"status": task.status}


@router.post("/tasks/{task_id}/check")
async def check(task_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    task = await _task(db, task_id)
    if task.status != "review" or not _can_check(task, profile, powers):
        raise HTTPException(status_code=403, detail="The task's author or a team lead checks it")
    task.status, task.checked_by, task.checked_at = "done", profile.id, _now()
    await db.commit()
    return {"status": task.status}


@router.post("/tasks/{task_id}/send-back")
async def send_back(task_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    task = await _task(db, task_id)
    if task.status != "review" or not _can_check(task, profile, powers):
        raise HTTPException(status_code=403, detail="The task's author or a team lead checks it")
    task.status = "taken"
    await db.commit()
    return {"status": task.status}


@router.post("/tasks/{task_id}/drop")
async def drop(task_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, _p = ctx
    task = await _task(db, task_id)
    if task.taken_by != profile.id or task.status != "taken":
        raise HTTPException(status_code=409, detail="Not your task")
    task.status, task.taken_by, task.taken_at = "open", None, None
    await db.commit()
    return {"status": task.status}


@router.post("/tasks/{task_id}/cancel")
async def cancel(task_id: uuid.UUID, ctx=Depends(signed_in), db: AsyncSession = Depends(get_db)):
    profile, powers = ctx
    task = await _task(db, task_id)
    if task.status != "open" or not (task.created_by == profile.id or powers.superuser):
        raise HTTPException(status_code=403, detail="Only its author can cancel an open task")
    task.status = "cancelled"
    await db.commit()
    return {"status": task.status}
