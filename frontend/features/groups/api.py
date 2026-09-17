from config.api import _get, _post, _patch, _delete


async def get_organizations():
    return await _get("/api/organizations/")


async def get_my_organizations(token: str):
    return await _get("/api/organizations/my_organizations", token=token)


async def update_organization(token: str, org_id: str, data: dict):
    return await _patch(f"/api/organizations/{org_id}", data, token=token)


# ── Healthsites ──────────────────────────────────────────────

async def create_healthsite(token: str, data: dict):
    return await _post("/api/healthsites/", data, token=token)


async def update_healthsite(token: str, healthsite_id: str, data: dict):
    return await _patch(f"/api/healthsites/{healthsite_id}", data, token=token)


async def delete_healthsite(token: str, healthsite_id: str):
    return await _delete(f"/api/healthsites/{healthsite_id}", token=token)


async def search_healthsites(token: str, data: dict):
    return await _post("/api/healthsites/search", data, token=token)


async def import_healthsite(token: str, facility: dict, role: str = "admin"):
    return await _post("/api/healthsites/import", {"facility": facility, "role": role}, token=token)
