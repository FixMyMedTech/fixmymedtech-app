from config.api import _get, _post, _patch, _delete


async def get_organizations():
    return await _get("/api/organizations/")


async def get_my_organizations(token: str):
    return await _get("/api/organizations/my_organizations", token=token)


async def get_organization_members(token: str, org_id: str):
    return await _get(f"/api/organizations/{org_id}/members", token=token)


async def search_profiles(token: str, org_id: str, q: str):
    from urllib.parse import quote
    return await _get(f"/api/organizations/{org_id}/search_profiles?q={quote(q)}", token=token)


async def add_organization_member(token: str, org_id: str, data: dict):
    return await _post(f"/api/organizations/{org_id}/members", data, token=token)


async def add_organization_member(token: str, org_id: str, data: dict):
    return await _post(f"/api/organizations/{org_id}/members", data, token=token)


async def remove_organization_member(token: str, org_id: str, member_id: str):
    return await _delete(f"/api/organizations/{org_id}/members/{member_id}", token=token)


async def leave_organization(token: str, org_id: str):
    return await _delete(f"/api/organizations/{org_id}/members/me", token=token)


async def delete_organization(token: str, org_id: str):
    return await _delete(f"/api/organizations/{org_id}", token=token)


async def update_organization_member(token: str, org_id: str, member_id: str, role: str):
    return await _patch(f"/api/organizations/{org_id}/members/{member_id}", {"role": role}, token=token)


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


async def import_healthsite(token: str, facility: dict, role: str = "technician"):
    return await _post("/api/healthsites/import", {"facility": facility, "role": role}, token=token)
