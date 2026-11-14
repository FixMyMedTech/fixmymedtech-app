# pages/invitation.py — /invite/{token}, the link in an invitation email.
#
# kind=clinic: an engineer invites a clinic. The page explains the vision and
# what the clinic gets, then creates the clinic account (→ clinic setup).
# kind=engineer: a clinic invites an engineer. Creates an engineer account
# (→ the three welcome quests); the clinic has already named them.
# Someone already signed in can accept with their current account.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api
from features.onboarding.ui import error_detail
from components import auth_shell, alert
from i18n import t as make_t
import os

rt = APIRouter()


def _start_session(req, res: dict) -> None:
    lang = req.session.get("lang", "en")
    req.session.clear()
    req.session["lang"] = lang
    req.session["token"] = res["access_token"]
    req.session["user_email"] = res["user"]["email"]


def _brand(_):
    return Span(Img(src=os.getenv("LOGO_URL") or "/static/fixmymedtech_africa.png",
                    style="height:56px;width:auto;display:block;margin-bottom:10px;"), cls="brand-icon")


def _intro(_, inv):
    if inv.get("kind") == "clinic":
        heading = _("ob.inv_clinic_heading").format(inviter=inv.get("inviter_name") or _("ob.an_engineer"))
        body = [P(_("ob.inv_clinic_vision"))]
        benefits = Ul(Li(_("ob.inv_benefit_qr")), Li(_("ob.inv_benefit_list")), Li(_("ob.inv_benefit_engineers")),
                      style="margin:0 0 14px 18px;color:var(--c-text-2);font-size:.9rem;")
        body.append(benefits)
    else:
        heading = _("ob.inv_engineer_heading").format(clinic=inv.get("clinic_name") or "")
        body = [P(_("ob.inv_engineer_body"))]
    msg = inv.get("message")
    if msg:
        body.append(Blockquote(msg, style="border-left:3px solid var(--c-primary);padding:6px 12px;"
                                         "margin:0 0 14px;color:var(--c-text-2);white-space:pre-line;"))
    return heading, body


def _page(req, _, token_str, inv, *, error="", full_name=""):
    heading, body = _intro(_, inv)
    signed_in = bool(auth_helper.get_token(req))
    if inv.get("status") != "sent":
        action = Div(P(_("ob.inv_used")),
                     A(_("login.signin"), href="/login", cls="btn btn-primary"))
    elif signed_in:
        action = Form(
            P(_("ob.inv_signed_in")),
            Button(_("ob.inv_claim"), type="submit", cls="btn btn-primary"),
            method="post", action=f"/invite/{token_str}/claim",
        )
    elif inv.get("has_account"):
        action = Div(P(_("ob.inv_has_account")),
                     A(_("login.signin"), href=f"/login?next=/invite/{token_str}", cls="btn btn-primary"))
    else:
        submit = _("ob.inv_create_clinic") if inv.get("kind") == "clinic" else _("ob.inv_create_engineer")
        action = Form(
            alert(error, "error"),
            Div(Label(_("signup.email_label"), cls="label"),
                Input(value=inv.get("email", ""), disabled=True, cls="input"), cls="form-group"),
            Div(Label(_("signup.full_name_label"), cls="label", for_="full_name"),
                Input(id="full_name", name="full_name", required=True, cls="input", value=full_name,
                      placeholder=_("signup.full_name_placeholder")), cls="form-group"),
            Div(
                Div(Label(_("signup.password_label"), cls="label", for_="password"),
                    Input(id="password", name="password", type="password", required=True, minlength="8",
                          cls="input", placeholder=_("signup.password_placeholder")), cls="form-group"),
                Div(Label(_("signup.confirm_label"), cls="label", for_="password2"),
                    Input(id="password2", name="password2", type="password", required=True, cls="input",
                          placeholder=_("signup.confirm_placeholder")), cls="form-group"),
                cls="form-row",
            ),
            Button(submit, type="submit", cls="btn btn-primary", style="width:100%;margin-top:8px;"),
            method="post", action=f"/invite/{token_str}",
        )
    return auth_shell(
        Div(
            Div(Div(_brand(_), H1(heading), cls="auth-brand"), *body, action, cls="auth-card"),
            Div(Blockquote(_("login.quote"), Em(_("login.quote_em")), '"', cls="auth-quote"), cls="auth-bg"),
            cls="auth-wrap",
        ),
        title=heading, lang=req.session.get("lang", "en"),
    )


async def _invitation_or_404(req, _, token_str):
    try:
        return await ob_api.get_invitation(token_str), None
    except Exception:
        return None, auth_shell(
            Div(Div(H2(_("ob.inv_not_found")), A(_("login.signin"), href="/login", cls="btn btn-primary"),
                    style="text-align:center;padding:60px 40px;"), style="max-width:440px;margin:80px auto;"),
            title=_("ob.inv_not_found"), lang=req.session.get("lang", "en"))


@rt("/invite/{token_str}")
async def get(req, token_str: str):
    _ = make_t(req.session.get("lang", "en"))
    inv, page = await _invitation_or_404(req, _, token_str)
    if page:
        return page
    return _page(req, _, token_str, inv)


@rt("/invite/{token_str}")
async def post(req, token_str: str, full_name: str = "", password: str = "", password2: str = ""):
    _ = make_t(req.session.get("lang", "en"))
    inv, page = await _invitation_or_404(req, _, token_str)
    if page:
        return page
    error = ""
    if not full_name.strip():
        error = _("signup.error_name")
    elif len(password) < 8:
        error = _("signup.error_password")
    elif password != password2:
        error = _("signup.error_mismatch")
    if not error:
        try:
            res = await ob_api.accept_invitation(token_str, full_name.strip(), password)
            _start_session(req, res)
            target = "/clinic/setup" if res.get("account_kind") == "clinic" else "/getting-started"
            return RedirectResponse(target, status_code=303)
        except httpx.HTTPStatusError as e:
            detail = error_detail(e)
            error = {"user_already_exists": _("ob.inv_has_account"),
                     "invitation_used": _("ob.inv_used")}.get(detail, _("ob.inv_failed"))
        except Exception:
            error = _("ob.inv_failed")
    return _page(req, _, token_str, inv, error=error, full_name=full_name)


@rt("/invite/{token_str}/claim")
async def post(req, token_str: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        res = await ob_api.claim_invitation(token, token_str)
    except Exception:
        return RedirectResponse(f"/invite/{token_str}", status_code=303)
    await auth_helper.refresh_onboarding(req, token)
    if res.get("kind") == "clinic":
        return RedirectResponse("/clinic/setup", status_code=303)
    return RedirectResponse("/getting-started", status_code=303)
