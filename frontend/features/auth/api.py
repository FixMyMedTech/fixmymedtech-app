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