from config.api import _get, _post, _patch


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
    return await _post("/api/devices", data, token)

async def update_device(token: str, device_id: str, data: dict):
    return await _patch(f"/api/devices/{device_id}", data, token)

async def update_location_device(token: str, device_id: str, data: dict):
    return await _patch(f"/api/devices/{device_id}/location", data, token)