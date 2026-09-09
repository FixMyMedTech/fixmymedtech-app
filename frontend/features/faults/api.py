from config.api import _get, _post, _patch, API_URL
import httpx


# ── Faults ───────────────────────────────────────────────────
async def submit_fault_public(data: dict):
    return await _post("/api/faults/public", data)

async def upload_fault_photo(token: str, fault_id: str, filename: str, content: bytes, content_type: str = None):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"photo": (filename, content, content_type or "application/octet-stream")}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL}/api/faults/{fault_id}/photo",
            files=files, headers=headers,
        )
        r.raise_for_status()
        return r.json()

async def get_fault_photo(token: str, fault_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/faults/{fault_id}/photo", headers=headers)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")

async def get_fault_photo_public(fault_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/faults/public/{fault_id}/photo")
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")

async def get_fault_assignees(token: str, device_id: str):
    return await _get(f"/api/faults/assignees/{device_id}", token)

async def get_fault(token: str, fault_id: str):
    return await _get(f"/api/faults/{fault_id}", token)

async def update_fault(token: str, fault_id: str, data: dict):
    return await _patch(f"/api/faults/{fault_id}", data, token)

async def get_fault_public(fault_id: str):
    return await _get(f"/api/faults/public/{fault_id}")