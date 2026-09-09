from fasthtml.common import *
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

import features.auth.api as auth_api
from i18n import t as make_t
from components import auth_shell

rt = APIRouter()


def _reset_card(_, errors=None):
    """Build the password-reset form card, optionally with error messages."""
    return Div(
        Div(
            Span(
                Img(src=os.getenv("LOGO_URL"),
                    style="height:56px; width:auto; display:block; margin-bottom:10px;"),
                cls="brand-icon"
            ),
            H1(_("reset.heading")),
            P(_("reset.subtitle")),
            cls="auth-brand"
        ),
        *([Div(e, cls="alert alert-error") for e in (errors or [])]),
        Div(
            Label(_("reset.password_label"), cls="label", for_="password"),
            Input(id="password", name="password", type="password",
                  placeholder=_("reset.password_placeholder"), cls="input"),
            cls="form-group"
        ),
        Div(
            Label(_("reset.confirm_label"), cls="label", for_="password2"),
            Input(id="password2", name="password2", type="password",
                  placeholder=_("reset.confirm_placeholder"), cls="input"),
            cls="form-group"
        ),
        Button(_("reset.submit"), type="submit", cls="btn btn-primary",
               style="width:100%;justify-content:center;margin-top:8px;"),
        P(_("reset.login_link"), A(_("reset.login_link_action"), href="/login"),
          cls="auth-link", style="margin-top:12px;"),
        cls="auth-card"
    )


def _reset_form(_, token, errors=None):
    return Form(
        Input(type="hidden", name="token", value=token),
        _reset_card(_, errors=errors),
        method="post", action="/reset-password"
    )


@rt("/reset-password")
async def get(req, token: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    if not token:
        return RedirectResponse("/login", status_code=302)
    return auth_shell(_reset_form(_, token), title=_("title.reset"), lang=lang)


@rt("/reset-password")
async def post(req, token: str, password: str, password2: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    errors = []
    if not token:                errors.append(_("reset.error_token"))
    if len(password) < 8:        errors.append(_("reset.error_password"))
    if password != password2:    errors.append(_("reset.error_mismatch"))

    if not errors:
        try:
            await auth_api.reset_password(token=token, password=password)
            return auth_shell(
                Div(
                    Div(
                        Div("✓", style="width:56px;height:56px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
                        H2(_("reset.done_heading")),
                        P(_("reset.done_msg")),
                        A(_("reset.done_btn"), href="/login", cls="btn btn-primary",
                          style="margin-top:20px;"),
                        style="text-align:center;padding:60px 40px;"
                    ),
                    style="max-width:440px;margin:80px auto;"
                ),
                title=_("title.reset"), lang=lang
            )
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                pass
            errors.append(detail or _("reset.error_failed"))
        except Exception as e:
            errors.append(str(e))

    return auth_shell(_reset_form(_, token, errors=errors),
                     title=_("title.reset"), lang=lang)