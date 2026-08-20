from config.api import _get, _patch


async def get_organizations():
    return await _get("/api/organizations/")


async def get_my_organizations(token: str):
    return await _get("/api/organizations/my_organizations", token=token)


async def update_organization(token: str, org_id: str, data: dict):
    return await _patch(f"/api/organizations/{org_id}", data, token=token)
