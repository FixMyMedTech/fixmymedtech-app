from config.api import _get, _patch


async def get_me(token: str):
    return await _get("/api/auth/me", token)


async def update_profile(token: str, data: dict):
    return await _patch("/api/auth/me", data, token=token)
