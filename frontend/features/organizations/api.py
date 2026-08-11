from config.api import _get, _post, _patch

async def get_organizations():
    return await _get("/api/organizations/")

async def get_my_organizations(token: str):
    return await _get("/api/organizations/my_organizations", token=token)