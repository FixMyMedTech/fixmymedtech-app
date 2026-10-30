from atexit import register

from fasthtml.common import FastHTML,serve, fast_app
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv
from fasthtml.common import *

load_dotenv()

from components import set_current_user, brand_head

from features.dashboard import pages as dashboard
from features.home import pages as home_pages
from features.devices.pages import device_list,device_detail,new_device,public_qr_page,guides,device_edit
from features.auth.pages import login as auth_login
from features.auth.pages import signup as auth_signup
from features.auth.pages import reset_password as auth_reset
from features.auth.pages import forgot_password as auth_forgot
from features.profile.pages import my_profile, profile_detail
from features.network import pages as network_pages
from features.feedback import pages as feedback_pages
from features.documents import pages as documents_pages
from features.tasks import pages as tasks_pages
from features.groups.pages import groups_page, organization_detail, organization_manage
from features.faults.pages import fault_list, report_page, fault_detail, public_fault
from features.maintenance.pages import public_log, maintenance_log, maintenance_log_detail
from i18n import LANGUAGES

SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-production")

# Cookie name is configurable so two stacks on the same host (browsers keep
# cookies per host, not per port) each keep their own login.
app, route = fast_app(secret_key=SECRET,
                      session_cookie=os.getenv("SESSION_COOKIE") or "session_",
                      static="/static/",
                      live=True,
                      hdrs=(
                        Script(src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"),
                        *brand_head(),
                    )
    )

app.mount("/static", StaticFiles(directory="static"), name="static")


# Browsers and crawlers ask for these at the site root, whatever the page says.
# They go first: fast_app's own static route would otherwise catch *.ico/*.png
# and look for them in this folder, not in static/.
from starlette.routing import Route

def _root_file(path, media_type):
    return lambda request: FileResponse(path, media_type=media_type)

app.router.routes[0:0] = [
    Route("/favicon.ico", _root_file("static/favicon.ico", "image/x-icon")),
    Route("/apple-touch-icon.png", _root_file("static/apple-touch-icon.png", "image/png")),
]


class UserContextMiddleware(BaseHTTPMiddleware):
    """Provide the current user's display info (name/username/email/avatar)
    to the avatar menu via a per-request context variable.

    /api/auth/me is queried once per session (the first authenticated request)
    and cached in the session; it is refreshed on login and when the profile
    is saved. No API call happens on page loads once cached.
    """
    async def dispatch(self, request, call_next):
        import features.auth.helper as auth_helper
        from config.api import token_rejected, access_pending

        # An expired token must not keep a private page "open": clear the
        # session first, so every require_auth() sends the visitor to /login.
        token = request.session.get("token", "")
        if token and auth_helper.token_expired(token):
            request.session.clear()
            request.state.session_expired = True
            token = ""

        # Filled in by config/api.py when the API answers 401 to our token.
        rejected = {}
        token_rejected.set(rejected)

        # Filled in by config/api.py when the API answers 403
        # community_access_pending (the account is a community applicant).
        pending = {}
        access_pending.set(pending)

        def from_session():
            return {
                "name": request.session.get("user_name", ""),
                "username": request.session.get("user_username", ""),
                "email": request.session.get("user_email", ""),
                "avatar": request.session.get("user_avatar", ""),
                "member_status": request.session.get("member_status", ""),
                "permissions": request.session.get("community_permissions", []),
            }

        data = {"name": "", "username": "", "email": "", "avatar": ""}
        if token:
            # member_status was added with the community journey: sessions
            # from before it are refreshed once.
            if request.session.get("user_name") and request.session.get("member_status"):
                data = from_session()
            else:
                try:
                    import features.profile.api as profile_api
                    me = await profile_api.get_me(token)
                    auth_helper.store_me(request, me)
                except Exception:
                    pass
                data = from_session()
        if rejected.get("rejected"):
            # Refused before the page even ran (e.g. after a JWT secret change).
            request.session.clear()
            request.state.session_expired = True
            data = {"name": "", "username": "", "email": "", "avatar": ""}
            rejected.clear()

        set_current_user(data)
        response = await call_next(request)

        if pending.get("pending") and request.session.get("token"):
            # The session thought this account was a member; it is an
            # applicant. Refresh the cache and show the start page.
            request.session["member_status"] = "applicant"
            if request.method == "GET" and request.headers.get("sec-fetch-mode") == "navigate" \
                    and not auth_helper.applicant_allowed(request.url.path):
                return RedirectResponse("/community/start", status_code=302)

        if rejected.get("rejected") and request.session.get("token"):
            # The page ran but the API refused the token. End the session and,
            # for a page load or form post, show login instead of the empty
            # page. Background fetches (e.g. "Load more") just get their
            # response, so they never append a login page.
            request.session.clear()
            request.state.session_expired = True
            if request.method == "POST" or request.headers.get("sec-fetch-mode") == "navigate":
                return auth_helper.login_redirect(request)
        return response


# Register INSIDE the session middleware FastHTML already installed (append =
# last-added = innermost), so request.session is populated when this runs and
# our writes are persisted by that session middleware.
app.user_middleware.append(Middleware(UserContextMiddleware))

@route("/lang")
async def post(req):
    form = await req.form()
    lang = form.get("lang", "en")
    if lang in LANGUAGES:
        req.session["lang"] = lang
    referer = req.headers.get("Referer", "/")
    return RedirectResponse(referer, status_code=302)

from features.community.pages import (
    join as community_join, start as community_start, journey as community_journey,
    tree as community_tree, role as community_role, welcome as community_welcome,
    admin_applicants, admin_members, admin_roles, admin_history,
)

auth_login.rt.to_app(app)
auth_signup.rt.to_app(app)
auth_reset.rt.to_app(app)
auth_forgot.rt.to_app(app)
# my_profile MUST register first: /profile/photo has to win over the
# /profile/{profile_id} pattern profile_detail adds.
my_profile.rt.to_app(app)
profile_detail.rt.to_app(app)
network_pages.rt.to_app(app)
tasks_pages.rt.to_app(app)
groups_page.rt.to_app(app)
organization_detail.rt.to_app(app)
organization_manage.rt.to_app(app)
device_detail.rt.to_app(app)
device_list.rt.to_app(app)
device_edit.rt.to_app(app)
dashboard.rt.to_app(app)
home_pages.rt.to_app(app)
public_qr_page.rt.to_app(app)
fault_list.rt.to_app(app)
public_fault.rt.to_app(app)
public_log.rt.to_app(app)
new_device.rt.to_app(app)
report_page.rt.to_app(app)
maintenance_log.rt.to_app(app)
fault_detail.rt.to_app(app)
maintenance_log_detail.rt.to_app(app)
guides.rt.to_app(app)
feedback_pages.rt.to_app(app)
documents_pages.rt.to_app(app)
# Community journey (docs/docs/community-journey.md)
community_join.rt.to_app(app)
community_start.rt.to_app(app)
community_welcome.rt.to_app(app)
community_tree.rt.to_app(app)
community_role.rt.to_app(app)
community_journey.rt.to_app(app)
admin_applicants.rt.to_app(app)
admin_members.rt.to_app(app)
admin_roles.rt.to_app(app)
admin_history.rt.to_app(app)

serve()
