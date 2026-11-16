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


# ── Wave 5: claims to validate and the task board (routers/community_work.py) ──
async def claim_options(token: str):
    return await _get("/api/community/claims/options", token)


async def make_claim(token: str, data: dict):
    return await _post("/api/community/claims", data, token)


async def add_claim_proof(token: str, claim_id: str, filename: str, content: bytes, content_type: str = None):
    import httpx
    from config.api import API_URL, _raise
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}/api/community/claims/{claim_id}/proof",
                              files={"photo": (filename, content, content_type or "application/octet-stream")},
                              headers={"Authorization": f"Bearer {token}"})
        _raise(r)
        return r.json()


async def get_claim_proof(token: str, claim_id: str):
    import httpx
    from config.api import API_URL
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/community/claims/{claim_id}/proof",
                             headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")


async def my_claims(token: str):
    return await _get("/api/community/claims/mine", token)


async def claims_to_review(token: str):
    return await _get("/api/community/claims/review", token)


async def answer_claim(token: str, claim_id: str, note: str):
    return await _patch(f"/api/community/claims/{claim_id}", {"note": note}, token)


async def review_claim(token: str, claim_id: str, action: str, note: str = ""):
    """action: confirm | more | decline"""
    return await _post(f"/api/community/claims/{claim_id}/{action}", {"note": note or None}, token)


async def task_board(token: str):
    return await _get("/api/community/tasks", token)


async def create_task(token: str, data: dict):
    return await _post("/api/community/tasks", data, token)


async def find_manual(token: str, manufacturer: str, model: str, device_id: str = None):
    return await _post("/api/community/tasks/find-manual",
                       {"manufacturer": manufacturer or None, "model": model, "device_id": device_id or None}, token)


async def task_action(token: str, task_id: str, action: str, data: dict | None = None):
    """action: take | done | check | send-back | drop | cancel"""
    return await _post(f"/api/community/tasks/{task_id}/{action}", data or {}, token)
