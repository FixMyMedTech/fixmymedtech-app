from fasthtml.common import *
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.api as auth_api
import features.organizations.api as org_api
import features.dashboard.api as dashboard_api

import features.auth.helper as auth_helper
from i18n import t as make_t
from components import pub_shell
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@rt("/login")
async def get(req, expired: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    # Only redirect if token is actually still valid
    token = auth_helper.get_token(req)
    if token:
        try:
            await dashboard_api.get_dashboard_stats(token)
            return RedirectResponse("/dashboard", status_code=302)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                auth_helper.clear_session(req)  # clear expired token, show login
        except Exception:
            return RedirectResponse("/dashboard", status_code=302)

    expired_msg = Div(_("login.expired"),
                    cls="alert alert-warning") if expired else ""
    form = Form(
        Div(
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
async def post(req, email: str, password: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        res = await auth_api.login(email, password)
        req.session["token"] = res["access_token"]
        req.session["user_email"] = res["user"]["email"]
        return RedirectResponse("/dashboard", status_code=302)
    except httpx.HTTPStatusError:
        form_error = Div(
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
                Div(_("login.error"), cls="alert alert-error"),
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


@rt("/signup")
async def get(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    if auth_helper.get_token(req):
        return RedirectResponse("/dashboard", status_code=302)

    try:
        orgs = await org_api.get_organizations()
    except Exception:
        orgs = []

    org_options = [Option(_("signup.select_org"), value="")]
    org_options += [Option(f"{o['name']} ({o['country']})", value=o["id"]) for o in orgs]

    content = Div(
        Div(
            Div(
                Span(
                    Img(src=os.getenv("LOGO_URL"),
                    style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                    cls="brand-icon"),
                H1(_("signup.heading")),
                P(_("signup.subtitle")),
                cls="auth-brand"
            ),
            Div(
                Label(_("signup.full_name_label"), cls="label", for_="full_name"),
                Input(id="full_name", name="full_name", type="text",
                    placeholder=_("signup.full_name_placeholder"), cls="input"),
                cls="form-group"
            ),
            Div(
                Label(_("signup.email_label"), cls="label", for_="email"),
                Input(id="email", name="email", type="email",
                    placeholder=_("signup.email_placeholder"), cls="input"),
                cls="form-group"
            ),
            Div(
                Div(
                    Label(_("signup.password_label"), cls="label", for_="password"),
                    Input(id="password", name="password", type="password",
                        placeholder=_("signup.password_placeholder"), cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label(_("signup.confirm_label"), cls="label", for_="password2"),
                    Input(id="password2", name="password2", type="password",
                        placeholder=_("signup.confirm_placeholder"), cls="input"),
                    cls="form-group"
                ),
                cls="form-row"
            ),
            Div(
                Label(_("signup.role_label"), cls="label"),
                Div(
                    Label(Input(type="radio", name="role", value="clinical_staff", checked=True),
                        _("signup.role_clinical")),
                    Label(Input(type="radio", name="role", value="technician"),
                        _("signup.role_technician")),
                    Label(Input(type="radio", name="role", value="admin"),
                        _("signup.role_admin")),
                    style="display:flex;flex-direction:column;gap:6px;font-size:0.875rem;"
                ),
                cls="form-group"
            ),
            Button(_("signup.submit"), type="submit", cls="btn btn-primary",
                style="width:100%;justify-content:center;margin-top:8px;"),
            P(_("signup.login_link"), A(_("signup.login_link_action"), href="/login"),
            cls="auth-link", style="margin-top:12px;"),
            cls="auth-card"
        ),
        Div(
            Div(
                Div(
                    Span("1", cls="step-num"), 
                    Div(P(_("signup.step1_heading"), style="color:#fff;font-weight:500;margin:0;"),
                        P(_("signup.step1_desc"),
                        style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                    style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
                ),
                Div(
                    Span("2", cls="step-num"),
                    Div(P(_("signup.step2_heading"), style="color:#fff;font-weight:500;margin:0;"),
                        P(_("signup.step2_desc"),
                        style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                    style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
                ),
                Div(
                    Span("3", cls="step-num"),
                    Div(P(_("signup.step3_heading"), style="color:#fff;font-weight:500;margin:0;"),
                        P(_("signup.step3_desc"),
                        style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                    style="display:flex;gap:14px;align-items:flex-start;"
                ),
            ),
            cls="auth-bg"
        ),
        cls="auth-wrap"
    )

    return pub_shell(
        Form(content, method="post", action="/signup"),
        title=_("title.signup"), lang=lang
    )


@rt("/signup")
async def post(req, full_name: str, email: str, password: str,
            password2: str, role: str, organization_id: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    errors = []
    if not full_name:     errors.append(_("signup.error_name"))
    if not email:         errors.append(_("signup.error_email"))
    if len(password) < 8: errors.append(_("signup.error_password"))
    if password != password2: errors.append(_("signup.error_mismatch"))

    if not errors:
        try:
            await auth_api.signup(
                email=email, password=password, full_name=full_name,
                role=role, organization_id=organization_id or None
            )
            success = pub_shell(
                Div(
                    Div(
                        Div("✓", style="width:56px;height:56px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
                        H2(_("signup.success_heading")),
                        P(_("signup.success_msg"), Strong(email),
                        _("signup.success_msg2")),
                        A(_("signup.success_btn"), href="/login", cls="btn btn-primary",
                        style="margin-top:20px;"),
                        style="text-align:center;padding:60px 40px;"
                    ),
                    style="max-width:440px;margin:80px auto;"
                ),
                title=_("title.signup"), lang=lang
            )
            return success
        except Exception as e:
            errors.append(str(e))

    if errors:
        error_msg = Div(*[Div(e, cls="alert alert-error") for e in errors])

        signup_form = Div(
            Div(
                Div(
                    Span(
                        Img(src=os.getenv("LOGO_URL"),
                        style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                        cls="brand-icon"),
                    H1(_("signup.heading")),
                    P(_("signup.subtitle")),
                    cls="auth-brand"
                ),
                error_msg,
                Div(
                    Label(_("signup.full_name_label"), cls="label", for_="full_name"),
                    Input(id="full_name", name="full_name", type="text",
                        placeholder=_("signup.full_name_placeholder"), cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label(_("signup.email_label"), cls="label", for_="email"),
                    Input(id="email", name="email", type="email",
                        placeholder=_("signup.email_placeholder"), cls="input"),
                    cls="form-group"
                ),
                Div(
                    Div(
                        Label(_("signup.password_label"), cls="label", for_="password"),
                        Input(id="password", name="password", type="password",
                            placeholder=_("signup.password_placeholder"), cls="input"),
                        cls="form-group"
                    ),
                    Div(
                        Label(_("signup.confirm_label"), cls="label", for_="password2"),
                        Input(id="password2", name="password2", type="password",
                            placeholder=_("signup.confirm_placeholder"), cls="input"),
                        cls="form-group"
                    ),
                    cls="form-row"
                ),
                Div(
                    Label(_("signup.role_label"), cls="label"),
                    Div(
                        Label(Input(type="radio", name="role", value="clinical_staff", checked=True),
                            _("signup.role_clinical")),
                        Label(Input(type="radio", name="role", value="technician"),
                            _("signup.role_technician")),
                        Label(Input(type="radio", name="role", value="admin"),
                            _("signup.role_admin")),
                        style="display:flex;flex-direction:column;gap:6px;font-size:0.875rem;"
                    ),
                    cls="form-group"
                ),
                Button(_("signup.submit"), type="submit", cls="btn btn-primary",
                    style="width:100%;justify-content:center;margin-top:8px;"),
                P(_("signup.login_link"), A(_("signup.login_link_action"), href="/login"),
                cls="auth-link", style="margin-top:12px;"),
                cls="auth-card"
            ),
            Div(
                Div(
                    Div(
                        Span("1", cls="step-num"), 
                        Div(P(_("signup.step1_heading"), style="color:#fff;font-weight:500;margin:0;"),
                            P(_("signup.step1_desc"),
                            style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                        style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
                    ),
                    Div(
                        Span("2", cls="step-num"),
                        Div(P(_("signup.step2_heading"), style="color:#fff;font-weight:500;margin:0;"),
                            P(_("signup.step2_desc"),
                            style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                        style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
                    ),
                    Div(
                        Span("3", cls="step-num"),
                        Div(P(_("signup.step3_heading"), style="color:#fff;font-weight:500;margin:0;"),
                            P(_("signup.step3_desc"),
                            style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                        style="display:flex;gap:14px;align-items:flex-start;"
                    ),
                ),
                cls="auth-bg"
            ),
            cls="auth-wrap"
        )

        return pub_shell(
            Form(signup_form, method="post", action="/signup"),
            title=_("title.signup"), lang=lang
        )
