from config.api import _get, _post, _patch, API_URL
import httpx


# ── Devices ──────────────────────────────────────────────────
async def get_devices(token: str, status: str = None):
    path = f"/api/devices/?status={status}" if status else "/api/devices/"
    return await _get(path, token)

async def get_device(token: str, device_id: str):
    return await _get(f"/api/devices/{device_id}", token)

async def get_device_public(device_id: str):
    return await _get(f"/api/devices/public/{device_id}")

async def get_categories():
    return await _get("/api/devices/categories")

async def create_device(token: str, data: dict):
    return await _post("/api/devices/", data, token)

async def update_device(token: str, device_id: str, data: dict):
    return await _patch(f"/api/devices/{device_id}", data, token)

async def upload_device_photo(token: str, device_id: str, filename: str, content: bytes, content_type: str = None):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"photo": (filename, content, content_type or "application/octet-stream")}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL}/api/devices/{device_id}/photo",
            files=files, headers=headers,
        )
        r.raise_for_status()
        return r.json()

async def get_device_photo(token: str, device_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/devices/{device_id}/photo", headers=headers)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")

async def update_location_device(token: str, device_id: str, data: dict):
    return await _patch(f"/api/devices/{device_id}/location", data, token)