from fasthtml.common import *
from starlette.responses import RedirectResponse
from urllib.parse import urlencode
import base64, json, os, time, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.api as auth_api
import features.dashboard.api as dashboard_api

# ── Auth helpers ─────────────────────────────────────────────

def get_token(req):
    return req.session.get("token")

def clear_session(req):
    """Clear all session data — call when token is invalid/expired."""
    req.session.clear()


def token_expired(token: str) -> bool:
    """True when the JWT's exp claim has passed, or the token can't be read.

    Read locally from the payload (no API call, no signature check): it only
    decides when to stop trusting the session. The API still verifies every
    token it receives."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except Exception:
        return True
    return exp is not None and exp <= time.time()


def login_redirect(req):
    """Send a signed-out visitor to /login: with the "session expired" notice
    when their session just ended, and back to the page they wanted (GET only)."""
    params = {}
    if getattr(req.state, "session_expired", False):
        params["expired"] = "1"
    if req.method == "GET":
        params["next"] = req.url.path + (f"?{req.url.query}" if req.url.query else "")
    url = "/login" + (f"?{urlencode(params)}" if params else "")
    return RedirectResponse(url, status_code=302 if req.method == "GET" else 303)

async def verify_token(req) -> bool:
    """
    Verify the token is still valid by calling a lightweight API endpoint.
    Returns True if valid, False if expired or invalid.
    """
    token = get_token(req)
    if not token:
        return False
    try:
        await dashboard_api.get_dashboard_stats(token)
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_session(req)
            return False
        return True  # other errors (500 etc) don't mean token is invalid
    except Exception:
        return True  # network errors don't mean token is invalid

def user_can_edit(me, device_org_id):
    """Check if user has admin/technician role in the device's organization."""
    for org in me.get("organizations", []):
        if org["id"] == device_org_id and org.get("role") in ("admin", "technician"):
            return True
    return False


def admin_org_ids(me) -> set:
    return {str(o["id"]) for o in me.get("organizations", []) if o.get("role") == "admin"}


def can_manage_device(me, device) -> bool:
    """Delete rights: admin of the owning organization, admin of the
    healthsite, or the user who registered the device. Mirrors the backend's
    _can_manage_device and deliberately excludes the maintaining organization."""
    admin = admin_org_ids(me)
    if str(device.get("organization_id") or "") in admin:
        return True
    if str(device.get("healthsite_id") or "") in admin:
        return True
    return bool(me.get("id")) and str(device.get("registered_by") or "") == str(me["id"])


def can_edit_device(me, device) -> bool:
    """Edit rights: everyone who can manage it, plus the admin of the
    organization that maintains it. Mirrors the backend's _can_edit_device."""
    if can_manage_device(me, device):
        return True
    return str(device.get("organization_maintenance_id") or "") in admin_org_ids(me)


def can_set_maintenance_org(me, device) -> bool:
    """Owning-org admin, healthsite admin, or current maintenance-org admin.
    Mirrors the backend's _can_set_maintenance_org."""
    admin = admin_org_ids(me)
    for key in ("organization_id", "healthsite_id", "organization_maintenance_id"):
        value = device.get(key)
        if value and str(value) in admin:
            return True
    return False


def user_can_edit_fault(me, fault):
    """Only the profile that reported or is assigned to a fault may edit it."""
    user_id = str(me.get("id", ""))
    return user_id and (
        user_id == str(fault.get("reported_by", ""))
        or user_id == str(fault.get("assigned_to", ""))
    )


# ── Fault workflow ──────────────────────────────────────────
# Mirrors the guards in backend/routers/fault_reports.py. The backend is the
# authority; these only decide which forms the page renders.

def _role_in(me, org_id, roles) -> bool:
    if not org_id:
        return False
    for org in me.get("organizations", []):
        if str(org.get("id")) == str(org_id) and org.get("role") in roles:
            return True
    return False


def is_fault_assignee(me, fault) -> bool:
    user_id = str(me.get("id", ""))
    return bool(user_id) and user_id == str(fault.get("assigned_to") or "")


def can_assign_fault(me, fault) -> bool:
    """Step 2 — the maintenance organization's admin."""
    return _role_in(me, (fault.get("device") or {}).get("organization_maintenance_id"), ("admin",))


def can_approve_fault(me, fault) -> bool:
    """Step 4 — the healthsite admin; a device with no healthsite falls back
    to the maintenance organization's admin."""
    device = fault.get("device") or {}
    healthsite = device.get("healthsite_id")
    if healthsite:
        return _role_in(me, healthsite, ("admin",))
    return _role_in(me, device.get("organization_maintenance_id"), ("admin",))


def fault_actions(me, fault) -> list:
    """Which workflow steps this user may act on right now, in order."""
    status = fault.get("status")
    out = []
    if status in ("open", "assigned") and can_assign_fault(me, fault):
        out.append("assign")
    if status == "assigned" and is_fault_assignee(me, fault):
        out.append("diagnosis")
    if status == "diagnosed" and can_approve_fault(me, fault):
        out.append("approval")
    if status == "approved" and is_fault_assignee(me, fault):
        out.append("start")
    if status in ("approved", "in_progress") and is_fault_assignee(me, fault):
        out.append("resolve")
    return out


def user_can_edit_log(me, log):
    """Only the profile that started or is assigned to a maintenance log may edit it."""
    user_id = str(me.get("id", ""))
    return user_id and (
        user_id == str(log.get("performed_by", ""))
        or user_id == str(log.get("assigned_to", ""))
    )

def require_auth(req):
    """
    Fast check — just verifies session has a token.
    For full token validation use require_auth_verified.
    """
    token = get_token(req)
    if not token:
        return None, login_redirect(req)
    return token, None

async def require_auth_verified(req):
    """
    Full check — verifies token is still valid with the API.
    Use on sensitive routes like dashboard.
    """
    token = get_token(req)
    if not token:
        return None, login_redirect(req)
    try:
        # Validate by hitting a protected endpoint
        await dashboard_api.get_dashboard_stats(token)
        return token, None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_session(req)
            return None, RedirectResponse("/login?expired=1", status_code=302)
        return token, None
    except Exception:
        return token, None
