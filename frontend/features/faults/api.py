from config.api import _get, _post, _patch


# ── Faults ───────────────────────────────────────────────────
async def submit_fault_public(data: dict):
    return await _post("/api/faults/public", data)