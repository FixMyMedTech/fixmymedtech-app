import httpx

from config.api import _get, _patch, API_URL


async def get_me(token: str):
    return await _get("/api/auth/me", token)


async def get_profile_stats(token: str):
    return await _get("/api/auth/me/stats", token)


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