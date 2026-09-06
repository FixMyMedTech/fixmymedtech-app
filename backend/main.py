# ============================================================
# FixMyMedTech — FastAPI Backend
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import Request
import httpx
import logging

from models import models
from config.db_config import engine
from routers import devices, fault_reports, maintenance_logs, dashboard, auth, organizations, oauth
from routers.admin_email import router as admin_email_router
from migrations import run_migrations
from utils.create_superuser import bootstrap_superuser_from_env

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply pending DB migrations before serving traffic
    try:
        await run_migrations(engine)
    except Exception as e:
        print(f"[migrations] ERROR: {e}")
        raise
    # Optionally ensure a superuser exists (env-driven, no-op by default)
    try:
        await bootstrap_superuser_from_env()
    except Exception as e:
        print(f"[bootstrap] ERROR: {e}")
    yield

app = FastAPI(
    title="FixMyMedTech API",
    description="Medical equipment management for LMICs",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5001")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Required for admin session auth (shared secret with AdminAuth backend)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("AUTH_SESSION_SECRET", "dev-admin-session-secret"),
    same_site="lax",
)

# Register OAuth providers (Google/GitHub) if configured
from config.oauth import register_oauth
register_oauth(app)

app.include_router(auth.router,             prefix="/api/auth",              tags=["auth"])
app.include_router(oauth.router,            prefix="/api/auth",              tags=["auth"])
app.include_router(devices.router,          prefix="/api/devices",           tags=["devices"])
app.include_router(fault_reports.router,    prefix="/api/faults",            tags=["faults"])
app.include_router(maintenance_logs.router, prefix="/api/maintenance-logs",  tags=["maintenance-logs"])
app.include_router(dashboard.router,        prefix="/api/dashboard",         tags=["dashboard"])
app.include_router(organizations.router,    prefix="/api/organizations",     tags=["organizations"])
app.include_router(admin_email_router,      prefix="/admin-panel",           tags=["admin"])

# ── SQLAdmin (browsable admin UI at /admin) ─────────────────
from sqladmin import Admin, ModelView
from admin_auth import AdminAuth

class ProfileAdmin(ModelView, model=models.Profile):
    column_list = [models.Profile.id, models.Profile.username, models.Profile.full_name, models.Profile.created_at]
    column_searchable_list = [models.Profile.username, models.Profile.full_name]
    column_sortable_list = [models.Profile.username, models.Profile.created_at]
    name = "Profile"
    name_plural = "Profiles"
    icon = "fa-solid fa-user"

class OrganizationAdmin(ModelView, model=models.Organization):
    column_list = [models.Organization.id, models.Organization.name, models.Organization.country, models.Organization.type]
    column_searchable_list = [models.Organization.name]
    name = "Organization"
    name_plural = "Organizations"
    icon = "fa-solid fa-hospital"

class DeviceAdmin(ModelView, model=models.Device):
    column_list = [models.Device.name, models.Device.manufacturer, models.Device.model, models.Device.status, models.Device.location]
    column_searchable_list = [models.Device.name, models.Device.serial_number]
    column_sortable_list = [models.Device.name, models.Device.status]
    name = "Device"
    name_plural = "Devices"
    icon = "fa-solid fa-microscope"

class FaultAdmin(ModelView, model=models.FaultReport):
    column_list = [models.FaultReport.id, models.FaultReport.device_id, models.FaultReport.severity, models.FaultReport.status, models.FaultReport.reported_at]
    column_sortable_list = [models.FaultReport.reported_at, models.FaultReport.severity, models.FaultReport.status]
    name = "Fault Report"
    name_plural = "Fault Reports"
    icon = "fa-solid fa-triangle-exclamation"

class MaintenanceLogAdmin(ModelView, model=models.MaintenanceLog):
    column_list = [models.MaintenanceLog.id, models.MaintenanceLog.device_id, models.MaintenanceLog.type, models.MaintenanceLog.status, models.MaintenanceLog.performed_at]
    column_sortable_list = [models.MaintenanceLog.performed_at, models.MaintenanceLog.type, models.MaintenanceLog.status]
    name = "Maintenance Log"
    name_plural = "Maintenance Logs"
    icon = "fa-solid fa-screwdriver-wrench"

class UserAdmin(ModelView, model=models.User):
    column_list = [models.User.id, models.User.email, models.User.full_name, models.User.is_active, models.User.is_verified, models.User.is_superuser, models.User.created_at]
    column_searchable_list = [models.User.email, models.User.full_name]
    column_sortable_list = [models.User.email, models.User.created_at]
    form_excluded_columns = [models.User.hashed_password, models.User.profile, models.User.updated_at]
    details_template = "user_details.html"
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-circle-user"

    # When a superuser creates a user in the admin portal, seed a random
    # password hash and send a verification email so they can set a password.
    async def on_model_change(self, data, model, is_created, request):
        # At this point model is constructed from an empty dict by SQLAdmin,
        # so attrs like model.email are still None.  We set them from `data`
        # so the row can be inserted correctly.
        from pwdlib import PasswordHash
        from pwdlib.hashers.bcrypt import BcryptHasher
        import secrets
        hasher = PasswordHash(hashers=[BcryptHasher()])

        # Normalize the email (lowercase) — also patch data so the subsequent
        # _set_attributes_async call writes the normalized value.
        email = (data.get("email") or "").strip().lower()
        data["email"] = email
        data["full_name"] = (data.get("full_name") or "").strip() or email.split("@")[0]
        data["is_verified"] = False
        data["is_active"] = bool(data.get("is_active"))
        data["is_superuser"] = bool(data.get("is_superuser"))
        data["hashed_password"] = hasher.hash(secrets.token_urlsafe(16))

    async def after_model_change(self, data, model, is_created, request):
        # Only on creation: create the 1:1 Profile + default org, and send a
        # verification email so the new user can set their password.
        if not is_created:
            return None

        from config.db_config import AsyncSessionLocal
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            # Ensure a Profile exists (1:1 with users.id)
            existing_profile = await session.execute(
                select(models.Profile).where(models.Profile.id == model.id)
            )
            if not existing_profile.scalar_one_or_none():
                session.add(models.Profile(
                    id=model.id,
                    username=model.email.split("@")[0].replace(".", "_"),
                    full_name=model.full_name or model.email,
                ))
                await session.flush()

            # Give a default org so the user is functional
            existing_org = await session.execute(
                select(models.OrgUser).where(models.OrgUser.profile_id == model.id)
            )
            if not existing_org.scalar_one_or_none():
                org = models.Organization(
                    name=model.full_name or model.email.split("@")[0],
                    country="",
                    type="hospital",
                )
                session.add(org)
                await session.flush()
                session.add(models.OrgUser(
                    profile_id=model.id,
                    organization_id=org.id,
                    role="admin",
                ))
            await session.commit()

        import os
        from fastapi_users.jwt import generate_jwt
        from pwdlib import PasswordHash
        from pwdlib.hashers.bcrypt import BcryptHasher
        from config.users import JWT_SECRET
        from config.email import send_invitation_email

        # Mint a reset-password token so the invitation link lets the new user
        # set their own password. FastAPI-Users' reset_password validates the
        # token against this exact audience and requires a `password_fgpt`
        # fingerprint of the user's current hashed password.
        token = generate_jwt(
            {
                "sub": str(model.id),
                "email": model.email,
                "password_fgpt": PasswordHash(hashers=[BcryptHasher()]).hash(model.hashed_password),
                "aud": "fastapi-users:reset",
            },
            JWT_SECRET,
            3600,  # 1 hour
        )
        base_url = os.getenv("FRONTEND_URL", "http://localhost:8888")
        try:
            await send_invitation_email(model.email, token, base_url)
        except Exception as exc:
            logger = logging.getLogger("admin")
            logger.exception("Invitation email to %s failed: %s", model.email, exc)
        return None

class OrgUserAdmin(ModelView, model=models.OrgUser):
    column_list = [models.OrgUser.id, models.OrgUser.profile_id, models.OrgUser.organization_id, models.OrgUser.role, models.OrgUser.created_at]
    column_sortable_list = [models.OrgUser.role, models.OrgUser.created_at]
    name = "Org User"
    name_plural = "Org Users"
    icon = "fa-solid fa-user-plus"

class DeviceCategoryAdmin(ModelView, model=models.DeviceCategory):
    column_list = [models.DeviceCategory.id, models.DeviceCategory.name, models.DeviceCategory.slug, models.DeviceCategory.icon]
    column_searchable_list = [models.DeviceCategory.name, models.DeviceCategory.slug]
    name = "Device Category"
    name_plural = "Device Categories"
    icon = "fa-solid fa-tags"

class DocumentAdmin(ModelView, model=models.Document):
    column_list = [models.Document.id, models.Document.title, models.Document.type, models.Document.language, models.Document.device_id, models.Document.url]
    column_searchable_list = [models.Document.title]
    column_sortable_list = [models.Document.title, models.Document.type, models.Document.created_at]
    name = "Document"
    name_plural = "Documents"
    icon = "fa-solid fa-file-lines"

admin = Admin(
    app, engine=engine, title="FixMyMedTech Admin",
    authentication_backend=AdminAuth(),
    templates_dir=os.path.join(os.path.dirname(__file__), "templates"),
)
admin.add_view(UserAdmin)
admin.add_view(ProfileAdmin)
admin.add_view(OrgUserAdmin)
admin.add_view(OrganizationAdmin)
admin.add_view(DeviceCategoryAdmin)
admin.add_view(DeviceAdmin)
admin.add_view(DocumentAdmin)
admin.add_view(FaultAdmin)
admin.add_view(MaintenanceLogAdmin)


@app.get("/health")
def health():
    return {"status": "ok", "service": "fixmymedtech-api"}


@app.get("/admin", include_in_schema=False)
async def redirect_admin():
    return RedirectResponse(url="/admin/", status_code=302)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    # Never proxy FastAPI's own routes (admin UI, docs, health, API, etc.)
    if path.startswith("admin") or path.startswith("docs") or \
       path == "openapi.json" or path.startswith("redoc") or path == "health" or \
       path.startswith("api"):
        return Response(status_code=404)

    query = request.url.query
    url = f"http://frontend:5001/{path}" + (f"?{query}" if query else "")
    headers = dict(request.headers)

    data = await request.body()

    try:
        async with httpx.AsyncClient() as client:
            if request.method == "GET":
                response = await client.get(url, headers=headers)
            elif request.method == "POST":
                response = await client.post(url, headers=headers, content=data)
            elif request.method == "PUT":
                response = await client.put(url, headers=headers, content=data)
            elif request.method == "DELETE":
                response = await client.delete(url, headers=headers, content=data)

        return Response(content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream unavailable")


@app.get('/')
def default_route():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888, forwarded_allow_ips="*")