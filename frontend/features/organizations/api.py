from config.api import _get, _post, _patch

async def get_organizations():
    return await _get("/api/organizations/")