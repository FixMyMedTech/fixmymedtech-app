from config.api import _get, _post, _patch


# ── Dashboard ────────────────────────────────────────────────
async def get_dashboard_stats(token: str):
    return await _get("/api/dashboard/stats", token)