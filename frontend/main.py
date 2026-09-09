from atexit import register

from fasthtml.common import FastHTML,serve, fast_app
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv
from fasthtml.common import *

load_dotenv()

from components import set_current_user

from features.dashboard import pages as dashboard
from features.home import pages as home_pages
from features.devices.pages import device_list,device_detail,new_device,public_qr_page,guides,maintenance_log,maintenance_log_detail
from features.auth.pages import login as auth_login
from features.auth.pages import signup as auth_signup
from features.auth.pages import reset_password as auth_reset
from features.profile import pages as profile_pages
from features.tasks import pages as tasks_pages
from features.groups.pages import groups_page
from features.faults.pages import report_page, fault_detail
from i18n import LANGUAGES

SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-production")

app, route = fast_app(secret_key=SECRET,
                      static="/static/",
                      live=True,
                      hdrs=(
                        Script(src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"),
                        Link(rel="icon", href="/favicon.ico"),
                    )
    )
                    
# put favicon.ico in your project root or /static
app.mount("/static", StaticFiles(directory="static"), name="static")


class UserContextMiddleware(BaseHTTPMiddleware):
    """Provide the current user's display info (name/username/email/avatar)
    to the avatar menu via a per-request context variable.

    /api/auth/me is queried once per session (the first authenticated request)
    and cached in the session; it is refreshed on login and when the profile
    is saved. No API call happens on page loads once cached.
    """
    async def dispatch(self, request, call_next):
        data = {"name": "", "username": "", "email": "", "avatar": ""}
        token = request.session.get("token", "")
        if token:
            if request.session.get("user_name"):
                data = {
                    "name": request.session.get("user_name", ""),
                    "username": request.session.get("user_username", ""),
                    "email": request.session.get("user_email", ""),
                    "avatar": request.session.get("user_avatar", ""),
                }
            else:
                try:
                    import features.profile.api as profile_api
                    me = await profile_api.get_me(token)
                    email = request.session.get("user_email", "") or ""
                    name = me.get("full_name") or me.get("username") or email
                    request.session["user_name"] = name
                    request.session["user_username"] = me.get("username") or name
                    request.session["user_email"] = email
                    request.session["user_avatar"] = me.get("avatar_key") or ""
                    data = {
                        "name": name,
                        "username": request.session["user_username"],
                        "email": request.session["user_email"],
                        "avatar": me.get("avatar_key") or "",
                    }
                except Exception:
                    data = {
                        "name": request.session.get("user_name", ""),
                        "username": request.session.get("user_username", ""),
                        "email": request.session.get("user_email", ""),
                        "avatar": request.session.get("user_avatar", ""),
                    }
        set_current_user(data)
        return await call_next(request)


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

auth_login.rt.to_app(app)
auth_signup.rt.to_app(app)
auth_reset.rt.to_app(app)
profile_pages.rt.to_app(app)
tasks_pages.rt.to_app(app)
groups_page.rt.to_app(app)
device_detail.rt.to_app(app)
device_list.rt.to_app(app)
dashboard.rt.to_app(app)
home_pages.rt.to_app(app)
public_qr_page.rt.to_app(app)
new_device.rt.to_app(app)
report_page.rt.to_app(app)
maintenance_log.rt.to_app(app)
fault_detail.rt.to_app(app)
maintenance_log_detail.rt.to_app(app)
guides.rt.to_app(app)

serve()