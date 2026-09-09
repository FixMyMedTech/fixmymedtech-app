from config.api import _get, _post, _patch


# ── Auth ─────────────────────────────────────────────────────
async def login(email: str, password: str):
    return await _post("/api/auth/login", {"email": email, "password": password})

async def signup(email: str, password: str, full_name: str):
    return await _post("/api/auth/signup", {
        "email": email, "password": password, "full_name": full_name,
    })

async def get_me(token: str):
    return await _get("/api/auth/me", token)

async def update_profile(token: str, data: dict):
    return await _patch("/api/auth/me", data, token=token)

async def get_my_tasks(token: str):
    return await _get("/api/auth/tasks", token)

async def forgot_password(email: str):
    return await _post("/api/auth/forgot-password", {"email": email})

async def reset_password(token: str, password: str):
    return await _post(f"/api/auth/reset-password?token={token}&password={password}", data={})