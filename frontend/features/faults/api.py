from config.api import _get, _post, _patch


# ── Faults ───────────────────────────────────────────────────
async def submit_fault_public(data: dict):
    return await _post("/api/faults/public", data)

async def get_fault_assignees(token: str, device_id: str):
    return await _get(f"/api/faults/assignees/{device_id}", token)

async def get_fault(token: str, fault_id: str):
    return await _get(f"/api/faults/{fault_id}", token)

async def update_fault(token: str, fault_id: str, data: dict):
    return await _patch(f"/api/faults/{fault_id}", data, token)

async def get_fault_public(fault_id: str):
    return await _get(f"/api/faults/public/{fault_id}")