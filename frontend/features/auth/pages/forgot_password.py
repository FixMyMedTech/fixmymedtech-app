from fasthtml.common import *
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

import features.auth.api as auth_api
from i18n import t as make_t
from components import auth_shell

rt = APIRouter()


def _steps_bg(_):
    """Numbered panel for the background column, same pattern as signup."""
    def step(n, heading, desc, last=False):
        return Div(
            Span(str(n), cls="step-num"),
            Div(
                P(heading, style="color:#fff;font-weight:500;margin:0;"),
                P(desc, style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin:0;")),
            style="display:flex;gap:14px;align-items:flex-start;"
                  + ("" if last else "margin-bottom:24px;")
        )
    return Div(
        Div(
            step(1, _("forgot.step1_heading"), _("forgot.step1_desc")),
            step(2, _("forgot.step2_heading"), _("forgot.step2_desc")),
            step(3, _("forgot.step3_heading"), _("forgot.step3_desc")),
            step(4, _("forgot.step4_heading"), _("forgot.step4_desc"), last=True),
            cls="auth-steps"
        ),
        cls="auth-bg"
    )


def _forgot_form(_, errors=None, values=None):
    """Email-only form that asks the API for a password reset link."""
    v = values or {}
    return Div(
        Div(
            Div(
                Span(
                    Img(src=os.getenv("LOGO_URL") or "/static/fixmymedtech_africa.png",
                        style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                    cls="brand-icon"),
                H1(_("forgot.heading")),
                P(_("forgot.subtitle")),
                cls="auth-brand"
            ),
            *([Div(e, cls="alert alert-error") for e in (errors or [])]),
            Div(
                Label(_("forgot.email_label"), cls="label", for_="email"),
                Input(id="email", name="email", type="email",
                      placeholder=_("forgot.email_placeholder"), cls="input",
                      value=v.get("email", "")),
                cls="form-group"
            ),
            Button(_("forgot.submit"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:4px;"),
            P(_("forgot.login_link"), A(_("forgot.login_link_action"), href="/login"),
              cls="auth-link", style="margin-top:12px;"),
            cls="auth-card"
        ),
        _steps_bg(_),
        cls="auth-wrap"
    )


@rt("/forgot-password")
async def get(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    return auth_shell(
        Form(_forgot_form(_), method="post", action="/forgot-password"),
        title=_("title.forgot"), lang=lang
    )


@rt("/forgot-password")
async def post(req, email: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    errors = []
    if not email:
        errors.append(_("forgot.error_email"))

    if not errors:
        try:
            await auth_api.forgot_password(email)
            # Always the same confirmation, whether or not the address is
            # registered, so this page can't be used to probe for accounts.
            return auth_shell(
                Div(
                    Div(
                        Div("📧", style="width:56px;height:56px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
                        H2(_("forgot.sent_heading")),
                        P(_("forgot.sent_msg"), Strong(email),
                          _("forgot.sent_msg2")),
                        A(_("forgot.sent_btn"), href="/login", cls="btn btn-primary",
                          style="margin-top:20px;"),
                        style="text-align:center;padding:60px 40px;"
                    ),
                    _steps_bg(_),
                    cls="auth-wrap"
                ),
                title=_("title.forgot"), lang=lang
            )
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                pass
            errors.append(detail or _("forgot.error_failed"))
        except Exception as e:
            errors.append(str(e))

    return auth_shell(
        Form(_forgot_form(_, errors=errors, values={"email": email}),
             method="post", action="/forgot-password"),
        title=_("title.forgot"), lang=lang
    )
