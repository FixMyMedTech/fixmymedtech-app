from config.api import _get, _post, _patch


# ── Maintenance logs ────────────────────────────────────────
async def create_maintenance_log(token: str, data: dict):
    return await _post("/api/maintenance-logs/", data, token)

async def get_maintenance_log(token: str, log_id: str):
    return await _get(f"/api/maintenance-logs/{log_id}", token)

async def get_maintenance_log_public(log_id: str):
    return await _get(f"/api/maintenance-logs/public/{log_id}")

async def update_maintenance_log(token: str, log_id: str, data: dict):
    return await _patch(f"/api/maintenance-logs/{log_id}", data, token)