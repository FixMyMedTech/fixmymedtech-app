from config.api import _get, _post, _patch


# ── Auth ─────────────────────────────────────────────────────
async def login(email: str, password: str):
    return await _post("/api/auth/login", {"email": email, "password": password})

async def signup(email: str, password: str, full_name: str, role: str, organization_id: str = None):
    data = {"email": email, "password": password, "full_name": full_name, "role": role}
    if organization_id:
        data["organization_id"] = organization_id
    return await _post("/api/auth/signup", data)

async def get_organizations():
    return await _get("/api/auth/organizations")