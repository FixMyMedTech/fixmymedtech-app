from fasthtml.common import *
from starlette.responses import RedirectResponse
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

import features.auth.api as auth_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import pub_shell

rt = APIRouter()


def _signup_form(t, errors=None, values=None):
    """Build the signup form card, optionally with error messages and filled values."""
    v = values or {}
    fields = Div(
        Div(
            Span(
                Img(src=os.getenv("LOGO_URL"),
                    style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                cls="brand-icon"),
            H1(t("signup.heading")),
            P(t("signup.subtitle")),
            cls="auth-brand"
        ),
        *([Div(e, cls="alert alert-error") for e in (errors or [])]),
        Div(
            Label(t("signup.full_name_label"), cls="label", for_="full_name"),
            Input(id="full_name", name="full_name", type="text",
                  placeholder=t("signup.full_name_placeholder"), cls="input",
                  value=v.get("full_name", "")),
            cls="form-group"
        ),
        Div(
            Label(t("signup.email_label"), cls="label", for_="email"),
            Input(id="email", name="email", type="email",
                  placeholder=t("signup.email_placeholder"), cls="input",
                  value=v.get("email", "")),
            cls="form-group"
        ),
        Div(
            Div(
                Label(t("signup.password_label"), cls="label", for_="password"),
                Input(id="password", name="password", type="password",
                      placeholder=t("signup.password_placeholder"), cls="input"),
                cls="form-group"
            ),
            Div(
                Label(t("signup.confirm_label"), cls="label", for_="password2"),
                Input(id="password2", name="password2", type="password",
                      placeholder=t("signup.confirm_placeholder"), cls="input"),
                cls="form-group"
            ),
            cls="form-row"
        ),
        Button(t("signup.submit"), type="submit", cls="btn btn-primary",
               style="width:100%;justify-content:center;margin-top:8px;"),
        P(t("signup.login_link"), A(t("signup.login_link_action"), href="/login"),
          cls="auth-link", style="margin-top:12px;"),
        cls="auth-card"
    )

    bg = Div(
        Div(
            Div(
                Span("1", cls="step-num"),
                Div(P(t("signup.step1_heading"), style="color:#fff;font-weight:500;margin:0;"),
                    P(t("signup.step1_desc"),
                      style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
            ),
            Div(
                Span("2", cls="step-num"),
                Div(P(t("signup.step2_heading"), style="color:#fff;font-weight:500;margin:0;"),
                    P(t("signup.step2_desc"),
                      style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                style="display:flex;gap:14px;align-items:flex-start;margin-bottom:24px;"
            ),
            Div(
                Span("3", cls="step-num"),
                Div(P(t("signup.step3_heading"), style="color:#fff;font-weight:500;margin:0;"),
                    P(t("signup.step3_desc"),
                      style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
                style="display:flex;gap:14px;align-items:flex-start;"
            ),
        ),
        cls="auth-bg"
    )

    return Div(fields, bg, cls="auth-wrap")


@rt("/signup")
async def get(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    if auth_helper.get_token(req):
        return RedirectResponse("/home", status_code=302)

    return pub_shell(
        Form(_signup_form(_), method="post", action="/signup"),
        title=_("title.signup"), lang=lang
    )


@rt("/signup")
async def post(req, full_name: str, email: str, password: str, password2: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    errors = []
    if not full_name:          errors.append(_("signup.error_name"))
    if not email:              errors.append(_("signup.error_email"))
    if len(password) < 8:      errors.append(_("signup.error_password"))
    if password != password2:  errors.append(_("signup.error_mismatch"))

    if not errors:
        try:
            await auth_api.signup(
                email=email, password=password, full_name=full_name,
            )
            return pub_shell(
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
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("detail", "")
            except Exception:
                pass
            if e.response.status_code == 409 and error_detail == "user_already_exists":
                return pub_shell(
                    Div(
                        Div(
                            Div("📧", style="width:56px;height:56px;background:var(--c-orange-lt,#fff3e0);color:var(--c-orange,#e65100);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
                            H2(_("signup.already_heading")),
                            P(_("signup.already_msg"), Strong(email),
                              _("signup.already_msg2")),
                            A(_("signup.already_btn"), href="/login", cls="btn btn-primary",
                              style="margin-top:20px;"),
                            style="text-align:center;padding:60px 40px;"
                        ),
                        style="max-width:440px;margin:80px auto;"
                    ),
                    title=_("title.signup"), lang=lang
                )
            errors.append(str(e))
        except Exception as e:
            errors.append(str(e))

    return pub_shell(
        Form(
            _signup_form(_, errors=errors, values={"full_name": full_name, "email": email}),
            method="post", action="/signup"
        ),
        title=_("title.signup"), lang=lang
    )
