import httpx
from urllib.parse import urlencode

from config.api import _get, _post, _patch, _delete, API_URL


async def get_me(token: str):
    return await _get("/api/auth/me", token)


async def get_profile_stats(token: str):
    return await _get("/api/auth/me/stats", token)


async def request_verification(token: str):
    """Email the signed-in user a new verification link."""
    return await _post("/api/auth/me/request-verification", {}, token)


async def discord_link_start(token: str) -> str:
    """URL to send the browser to for "Connect Discord"."""
    return (await _post("/api/auth/me/discord/link-start", {}, token))["url"]


async def discord_unlink(token: str):
    return await _delete("/api/auth/me/discord", token)


async def list_profiles(token: str, q: str = "", limit: int = 24, offset: int = 0,
                        sort: str = "", direction: str = ""):
    """The Network directory: every active member, ordered by activity.

    `sort`/`dir` are passed through verbatim — the backend whitelists them and
    echoes the effective values back, so an unknown value degrades to the
    composite leaderboard rather than erroring. `view` is deliberately absent:
    cards vs table is a presentation concern handled entirely in the page.
    """
    params = {"limit": limit, "offset": offset}
    if q and q.strip():
        params["q"] = q.strip()
    if sort:
        params["sort"] = sort
    if direction:
        params["dir"] = direction
    return await _get(f"/api/auth/profiles?{urlencode(params)}", token)


async def get_profile(token: str, profile_id: str):
    """Another user's profile, read-only. Any signed-in member may open it."""
    return await _get(f"/api/auth/profiles/{profile_id}", token)


async def get_profile_photo(token: str, profile_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/auth/profiles/{profile_id}/photo",
                             headers=headers)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")


async def update_profile(token: str, data: dict):
    return await _patch("/api/auth/me", data, token=token)


async def upload_avatar(token: str, filename: str, content: bytes, content_type: str = None):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"photo": (filename, content, content_type or "application/octet-stream")}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}/api/auth/me/photo", files=files, headers=headers)
        r.raise_for_status()
        return r.json()


async def get_avatar(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/auth/me/photo", headers=headers)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")