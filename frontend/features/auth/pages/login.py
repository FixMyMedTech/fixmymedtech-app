from fasthtml.common import *
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.api as auth_api
import features.dashboard.api as dashboard_api

import features.auth.helper as auth_helper
from i18n import t as make_t
from components import pub_shell
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# LOGIN ROUTES
# ══════════════════════════════════════════════════════════════

@rt("/login")
async def get(req, expired: str = "", next: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    # Only redirect if token is actually still valid
    token = auth_helper.get_token(req)
    if token:
        try:
            await dashboard_api.get_dashboard_stats(token)
            target = next if next.startswith("/") else "/dashboard"
            return RedirectResponse(target, status_code=302)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                auth_helper.clear_session(req)  # clear expired token, show login
        except Exception:
            return RedirectResponse("/dashboard", status_code=302)

    expired_msg = Div(_("login.expired"),
                    cls="alert alert-warning") if expired else ""
    form = Form(
        Div(
            Input(type="hidden", name="next", value=next),
            Div(
                Div(
                    Span(
                        Img(src=os.getenv("LOGO_URL"),
                        style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                        cls="brand-icon"
                    ),
                    H1(_("login.heading")),
                    P(_("login.subtitle")),
                    cls="auth-brand"
                ),
                expired_msg,
                Div(
                    Label(_("login.email_label"), cls="label", for_="email"),
                    Input(id="email", name="email", type="email",
                        placeholder=_("login.email_placeholder"), cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label(_("login.password_label"), cls="label", for_="password"),
                    Input(id="password", name="password", type="password",
                        placeholder=_("login.password_placeholder"), cls="input"),
                    cls="form-group"
                ),
                Button(_("login.signin"), type="submit", cls="btn btn-primary",
                    style="width:100%;justify-content:center;margin-top:4px;"),
                P(
                    _("login.signup_link"), A(_("login.signup_link_action"), href="/signup"),
                    cls="auth-link", style="margin-top:12px;"
                ),
                cls="auth-card"
            ),
            Div(
                Blockquote(
                    _("login.quote"),
                    Em(_("login.quote_em")),
                    '"',
                    cls="auth-quote"
                ),
                cls="auth-bg"
            ),
            cls="auth-wrap"
        ),
        method="post", action="/login"
    )

    return pub_shell(form, title=_("title.login"), lang=lang)


@rt("/login")
async def post(req, email: str, password: str, next: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        res = await auth_api.login(email, password)
        req.session["token"] = res["access_token"]
        req.session["user_email"] = res["user"]["email"]
        target = next if next.startswith("/") else "/dashboard"
        return RedirectResponse(target, status_code=302)
    except httpx.HTTPStatusError as e:
        error_key = _("login.error")
        error_detail = ""
        try:
            error_detail = e.response.json().get("detail", "")
        except Exception:
            pass
        if e.response.status_code == 404 and error_detail == "user_not_found":
            error_key = _("login.error_not_found")
        elif e.response.status_code == 403 and error_detail == "email_not_confirmed":
            error_key = _("login.error_not_confirmed")
        elif e.response.status_code == 401 and error_detail == "invalid_credentials":
            error_key = _("login.error")

        form_error = Div(
            Div(
                Input(type="hidden", name="next", value=next),
                Div(
                    Span(
                        Img(src=os.getenv("LOGO_URL"),
                        style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                        cls="brand-icon"
                    ),
                    H1(_("login.heading")),
                    P(_("login.subtitle")),
                    cls="auth-brand"
                ),
                Div(error_key, cls="alert alert-error"),
                Div(
                    Label(_("login.email_label"), cls="label", for_="email"),
                    Input(id="email", name="email", type="email",
                        value=email, cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label(_("login.password_label"), cls="label", for_="password"),
                    Input(id="password", name="password", type="password",
                        cls="input"),
                    cls="form-group"
                ),
                Button(_("login.signin"), type="submit", cls="btn btn-primary",
                    style="width:100%;justify-content:center;margin-top:4px;"),
                P(_("login.signup_link"), A(_("login.signup_link_action"), href="/signup"),
                cls="auth-link", style="margin-top:12px;"),
                cls="auth-card"
            ),
            Div(
                Blockquote(_("login.quote"),
                        Em(_("login.quote_em")), '"', cls="auth-quote"),
                cls="auth-bg"
            ),
            cls="auth-wrap"
        )
        return pub_shell(Form(form_error, method="post", action="/login"),
                        title=_("title.login"), lang=lang)


@rt("/logout")
async def get(req):
    req.session.clear()
    return RedirectResponse("/login", status_code=302)
