from config.api import _get


async def get_my_tasks(token: str):
    return await _get("/api/auth/tasks", token)
