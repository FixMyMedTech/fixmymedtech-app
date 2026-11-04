# api.py — wrappers for the community journey API (/api/community, backend/routers/community.py)

from urllib.parse import urlencode

from config.api import _get, _post, _patch, _delete


def _qs(**params) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    return f"?{urlencode(clean)}" if clean else ""


# ── Public ──
async def get_catalogue():
    return await _get("/api/community/catalogue")


async def get_config():
    return await _get("/api/community/config")


async def join(data: dict):
    return await _post("/api/community/join", data)


# ── Me ──
async def get_me(token: str):
    return await _get("/api/community/me", token)


async def intro_video_watched(token: str):
    return await _post("/api/community/me/quests/intro_video", {}, token)


async def set_consent(token: str, social: bool):
    return await _post("/api/community/me/consent", {"social": social}, token)


async def update_story(token: str, data: dict):
    return await _patch("/api/community/me/story", data, token)


# ── Dashboard ──
async def list_applicants(token: str, status: str = "pending", country: str = ""):
    return await _get(f"/api/community/admin/applicants{_qs(status=status, country=country)}", token)


async def get_applicant(token: str, profile_id: str):
    return await _get(f"/api/community/admin/applicants/{profile_id}", token)


async def update_applicant(token: str, profile_id: str, data: dict):
    return await _patch(f"/api/community/admin/applicants/{profile_id}", data, token)


async def meeting_held(token: str, profile_id: str):
    return await _post(f"/api/community/admin/applicants/{profile_id}/meeting-held", {}, token)


async def confirm_quest(token: str, profile_id: str, quest_key: str):
    return await _post(f"/api/community/admin/applicants/{profile_id}/quests/{quest_key}", {}, token)


async def refuse_applicant(token: str, profile_id: str, reason: str):
    return await _post(f"/api/community/admin/applicants/{profile_id}/refuse", {"reason": reason}, token)


async def reopen_applicant(token: str, profile_id: str):
    return await _post(f"/api/community/admin/applicants/{profile_id}/reopen", {}, token)


async def list_hosts(token: str):
    return await _get("/api/community/admin/hosts", token)


async def list_members(token: str, q: str = "", team: str = "", country: str = "", offset: int = 0):
    return await _get(f"/api/community/admin/members{_qs(q=q, team=team, country=country, offset=offset or None)}", token)


async def get_member(token: str, profile_id: str):
    return await _get(f"/api/community/admin/members/{profile_id}", token)


async def set_team(token: str, profile_id: str, data: dict):
    """data: {team_key, level: candidate|member|lead, reason}"""
    return await _post(f"/api/community/admin/members/{profile_id}/teams", data, token)


async def remove_from_team(token: str, place_id: str, reason: str):
    return await _delete(f"/api/community/admin/team-members/{place_id}{_qs(reason=reason)}", token)


async def recognise(token: str, profile_id: str, data: dict):
    """data: {achievement_key, count, note}"""
    return await _post(f"/api/community/admin/members/{profile_id}/achievements", data, token)


async def remove_record(token: str, record_id: str, reason: str):
    return await _delete(f"/api/community/admin/achievement-records/{record_id}{_qs(reason=reason)}", token)


async def edit_team(token: str, team_key: str, data: dict):
    return await _patch(f"/api/community/admin/teams/{team_key}", data, token)


async def history(token: str, offset: int = 0):
    return await _get(f"/api/community/admin/history{_qs(offset=offset or None)}", token)
