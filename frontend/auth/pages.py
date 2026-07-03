from fasthtml.common import *
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import auth.api as auth_api
import features.dashboard.api as dashboard_api

import auth.helper as auth_helper
from components import pub_shell
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@rt("/login")
async def get(req, expired: str = ""):
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

    expired_msg = Div("Your session has expired. Please sign in again.",
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
                    H1("FixMyMedTech"),
                    P("Medical equipment management for LMICs"),
                    cls="auth-brand"
                ),
                expired_msg,
                Div(
                    Label("Email", cls="label", for_="email"),
                    Input(id="email", name="email", type="email",
                        placeholder="you@hospital.org", cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label("Password", cls="label", for_="password"),
                    Input(id="password", name="password", type="password",
                        placeholder="••••••••", cls="input"),
                    cls="form-group"
                ),
                Button("Sign in", type="submit", cls="btn btn-primary",
                    style="width:100%;justify-content:center;margin-top:4px;"),
                P(
                    "New to FixMyMedTech? ", A("Create an account", href="/signup"),
                    cls="auth-link", style="margin-top:12px;"
                ),
                cls="auth-card"
            ),
            Div(
                Blockquote(
                    '"40–70% of medical equipment in LMICs is out of service. ',
                    Em("FixMyMedTech helps change that."),
                    '"',
                    cls="auth-quote"
                ),
                cls="auth-bg"
            ),
            cls="auth-wrap"
        ),
        method="post", action="/login"
    )

    return pub_shell(form, title="Login — FixMyMedTech")


@rt("/login")
async def post(req, email: str, password: str):
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
                    H1("FixMyMedTech"),
                    P("Medical equipment management for LMICs"),
                    cls="auth-brand"
                ),
                Div("Invalid email or password.", cls="alert alert-error"),
                Div(
                    Label("Email", cls="label", for_="email"),
                    Input(id="email", name="email", type="email",
                        value=email, cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label("Password", cls="label", for_="password"),
                    Input(id="password", name="password", type="password",
                        cls="input"),
                    cls="form-group"
                ),
                Button("Sign in", type="submit", cls="btn btn-primary",
                    style="width:100%;justify-content:center;margin-top:4px;"),
                P("New to FixMyMedTech? ", A("Create an account", href="/signup"),
                cls="auth-link", style="margin-top:12px;"),
                cls="auth-card"
            ),
            Div(
                Blockquote('"40–70% of medical equipment in LMICs is out of service. ',
                        Em("FixMyMedTech helps change that."), '"', cls="auth-quote"),
                cls="auth-bg"
            ),
            cls="auth-wrap"
        )
        return pub_shell(Form(form_error, method="post", action="/login"),
                        title="Login — FixMyMedTech")


@rt("/logout")
async def get(req):
    req.session.clear()
    return RedirectResponse("/login", status_code=302)


@rt("/signup")
async def get(req):
    if auth_helper.get_token(req):
        return RedirectResponse("/dashboard", status_code=302)

    try:
        orgs = await auth_api.get_organizations()
    except Exception:
        orgs = []

    org_options = [Option("— Select your organisation —", value="")]
    org_options += [Option(f"{o['name']} ({o['country']})", value=o["id"]) for o in orgs]

    content = Div(
        Div(
            Div(
                Span(
                    Img(src=os.getenv("LOGO_URL"),
                    style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                    cls="brand-icon"),
                H1("Create account"),
                P("Join FixMyMedTech to manage your hospital's equipment"),
                cls="auth-brand"
            ),
            Div(
                Label("Full name", cls="label", for_="full_name"),
                Input(id="full_name", name="full_name", type="text",
                    placeholder="Dr. Jane Smith", cls="input"),
                cls="form-group"
            ),
            Div(
                Label("Email", cls="label", for_="email"),
                Input(id="email", name="email", type="email",
                    placeholder="you@hospital.org", cls="input"),
                cls="form-group"
            ),
            Div(
                Div(
                    Label("Password", cls="label", for_="password"),
                    Input(id="password", name="password", type="password",
                        placeholder="Min. 8 characters", cls="input"),
                    cls="form-group"
                ),
                Div(
                    Label("Confirm password", cls="label", for_="password2"),
                    Input(id="password2", name="password2", type="password",
                        placeholder="Repeat password", cls="input"),
                    cls="form-group"
                ),
                cls="form-row"
            ),
            Div(
                Label("Organisation", cls="label", for_="org"),
                Select(*org_options, id="org", name="organization_id", cls="input"),
                cls="form-group"
            ),
            Div(
                Label("Role", cls="label"),
                Div(
                    Label(Input(type="radio", name="role", value="clinical_staff", checked=True),
                        " Clinical staff (nurse, doctor)"),
                    Label(Input(type="radio", name="role", value="technician"),
                        " Biomedical technician"),
                    Label(Input(type="radio", name="role", value="admin"),
                        " Hospital administrator"),
                    style="display:flex;flex-direction:column;gap:6px;font-size:0.875rem;"
                ),
                cls="form-group"
            ),
            Button("Create account", type="submit", cls="btn btn-primary",
                style="width:100%;justify-content:center;margin-top:8px;"),
            P("Already have an account? ", A("Sign in", href="/login"),
            cls="auth-link", style="margin-top:12px;"),
            cls="auth-card"
        ),
        Div(
            Div(
                Div(
                    Span("1", cls="step-num"), 
                    Div(P("Create your account", style="color:#fff;font-weight:500;margin:0;"),
                        P("Register with your hospital email",
                        style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                    style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
                ),
                Div(
                    Span("2", cls="step-num"),
                    Div(P("Confirm your email", style="color:#fff;font-weight:500;margin:0;"),
                        P("Click the link we send you",
                        style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                    style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
                ),
                Div(
                    Span("3", cls="step-num"),
                    Div(P("Start tracking", style="color:#fff;font-weight:500;margin:0;"),
                        P("Manage your equipment fleet",
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
        title="Sign up — FixMyMedTech"
    )


@rt("/signup")
async def post(req, full_name: str, email: str, password: str,
            password2: str, role: str, organization_id: str = ""):
    errors = []
    if not full_name:     errors.append("Full name is required.")
    if not email:         errors.append("Email is required.")
    if len(password) < 8: errors.append("Password must be at least 8 characters.")
    if password != password2: errors.append("Passwords do not match.")

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
                        H2("Check your email"),
                        P(f"We sent a confirmation link to ", Strong(email),
                        ". Click it to activate your account."),
                        A("Go to login", href="/login", cls="btn btn-primary",
                        style="margin-top:20px;"),
                        style="text-align:center;padding:60px 40px;"
                    ),
                    style="max-width:440px;margin:80px auto;"
                )
            )
            return success
        except Exception as e:
            errors.append(str(e))

    error_html = Div(*[Div(e, cls="alert alert-error") for e in errors])
    return RedirectResponse(f"/signup?error={'|'.join(errors)}", status_code=302)

