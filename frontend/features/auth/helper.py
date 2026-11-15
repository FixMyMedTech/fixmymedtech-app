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


# ── Onboarding (migration 030) ──────────────────────────────

def cache_onboarding(req, me: dict) -> None:
    """Keep the onboarding fields of /api/auth/me in the session; the sidebar
    and the clinic-setup redirect read them on every request. The welcome
    quests themselves are the community gate below (member_status)."""
    req.session["user_account_kind"] = me.get("account_kind") or ""
    req.session["user_is_talk_host"] = "1" if me.get("is_talk_host") else ""
    # Any place in a clinic counts: a nurse invited by the clinic has no
    # clinic of their own to set up (only a clinic account with none does).
    has_clinic = bool(me.get("organizations"))
    req.session["user_clinic_ready"] = "1" if has_clinic else ""
    # Who sees "Add device": engineers, and clinic admins. A nurse
    # (clinical_staff) reports and calls, but doesn't register devices.
    roles = {o.get("role") for o in me.get("organizations") or []}
    req.session["user_adds_devices"] = "1" if (
        (me.get("account_kind") or "engineer") == "engineer" or "admin" in roles or me.get("is_superuser")) else ""


def adds_devices(req) -> bool:
    """Show "Add device" (the API still decides per clinic)."""
    return req.session.get("user_adds_devices", "1") == "1"


def is_clinic_account(req) -> bool:
    return req.session.get("user_account_kind") == "clinic"


# Paths a clinic account still setting up its clinic can always open.
CLINIC_SETUP_OPEN_PREFIXES = (
    "/profile", "/logout", "/lang", "/static", "/d/", "/invite/", "/library",
    "/documents/", "/feedback", "/favicon.ico", "/apple-touch-icon.png", "/login",
    "/signup", "/join", "/forgot-password", "/reset-password", "/oauth-callback",
    "/clinic/", "/community/guides",
)


def onboarding_redirect(req) -> str | None:
    """Where to send this signed-in request instead, or None: a clinic
    account without its clinic yet goes to clinic setup."""
    path = req.url.path
    if path == "/" or path.startswith(CLINIC_SETUP_OPEN_PREFIXES):
        return None
    if req.session.get("user_account_kind") == "clinic" and not req.session.get("user_clinic_ready"):
        return "/clinic/setup"
    return None


async def refresh_onboarding(req, token: str) -> dict:
    """Re-read /api/auth/me and update the session (after a step changes the
    member status or the clinic). Returns me, or {} on failure."""
    try:
        me = await auth_api.get_me(token)
    except Exception:
        return {}
    store_me(req, me)
    # The sidebar of THIS response reads the per-request user context.
    from components import current_user_ctx
    ctx = current_user_ctx()
    ctx["member_status"] = req.session.get("member_status", "")
    ctx["permissions"] = req.session.get("community_permissions", [])
    ctx["account_kind"] = me.get("account_kind") or ""
    ctx["is_talk_host"] = bool(me.get("is_talk_host"))
    return me


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

# ── Community gate ───────────────────────────────────────────
# A community applicant (still doing the welcome quests) or a refused account
# can only open these pages; everything else redirects to /community/start.
# The backend enforces the same rule (403 community_access_pending).
APPLICANT_PATHS = ("/community/start", "/community/welcome", "/community/achievements",
                   "/community/tree", "/profile", "/logout", "/lang", "/feedback",
                   # Brief guardrail 1: a visitor already has the manual library.
                   "/library", "/documents",
                   # Invitation links and the onboarding entry point.
                   "/invite", "/getting-started", "/clinic",
                   # Wave 5: anyone signed in may ask for a missing manual.
                   "/community/tasks/find-manual",
                   # In-app help: the guides an applicant can use.
                   "/community/guides")


def applicant_allowed(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in APPLICANT_PATHS)


def is_applicant(req) -> bool:
    return req.session.get("member_status") in ("applicant", "refused")


def store_me(req, me: dict) -> None:
    """Cache what the shell needs from /api/auth/me in the session: avatar
    menu data, member status and community permissions (for the sidebar and
    the gate). Call it whenever the profile or the community status changes."""
    email = req.session.get("user_email", "") or me.get("email") or ""
    name = me.get("full_name") or me.get("username") or email
    community = me.get("community") or {}
    old_status = req.session.get("member_status")
    req.session["user_name"] = name
    req.session["user_username"] = me.get("username") or name
    req.session["user_email"] = email
    req.session["user_avatar"] = me.get("avatar_key") or ""
    req.session["member_status"] = me.get("member_status") or "member"
    req.session["community_permissions"] = list(community.get("permissions") or [])
    req.session["community_teams"] = dict(community.get("teams") or {})
    if old_status in ("applicant", "staff") and req.session["member_status"] == "member":
        # Shown once: the "You're a member" welcome page.
        req.session["show_welcome"] = "1"
    cache_onboarding(req, me)


def require_auth(req):
    """
    Fast check — just verifies session has a token.
    For full token validation use require_auth_verified.

    Also the community gate: an applicant is sent to /community/start for
    every page outside APPLICANT_PATHS.
    """
    token = get_token(req)
    if not token:
        return None, login_redirect(req)
    if is_applicant(req) and not applicant_allowed(req.url.path):
        return token, RedirectResponse("/community/start", status_code=302 if req.method == "GET" else 303)
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
