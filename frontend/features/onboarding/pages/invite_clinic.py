# pages/invite_clinic.py — /invite-clinic
#
# An engineer whose welcome quests are done invites a clinic by email with a
# short message, and follows each invitation: sent → account created → clinic
# set up → confirmed / not now. The inviting engineer stays recorded on the
# clinic whatever it answers.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api
from features.onboarding.ui import ONBOARDING_CSS, error_detail
from components import page_shell, status_badge, fmt_date, alert
from i18n import t as make_t

rt = APIRouter()


def _page(_, me, invitations, *, sent=None, error="", values=None):
    v = values or {}
    if not me.get("can_invite_clinics"):
        form_card = Div(
            H3(_("ob.invite_locked_heading"), cls="card-title"),
            P(_("ob.invite_locked_body")),
            A(_("ob.see_quests"), href="/getting-started", cls="btn btn-primary"),
            cls="card ob-locked", style="max-width:720px;",
        )
    else:
        form_card = Div(
            H3(_("ob.invite_form_heading"), cls="card-title"),
            P(_("ob.invite_form_body"), style="color:var(--c-text-2);margin-bottom:14px;"),
            alert(_("ob.invite_sent").format(email=sent), "success") if sent else "",
            alert(error, "error"),
            Form(
                Div(Label(_("ob.invite_email"), cls="label", for_="email"),
                    Input(id="email", name="email", type="email", required=True, cls="input",
                          value=v.get("email", ""), placeholder=_("ob.invite_email_placeholder")),
                    cls="form-group"),
                Div(Label(_("ob.invite_message"), cls="label", for_="message"),
                    Textarea(v.get("message", ""), id="message", name="message", rows="4", cls="input",
                             maxlength="1000", placeholder=_("ob.invite_message_placeholder")),
                    cls="form-group"),
                Button(_("ob.invite_submit"), type="submit", cls="btn btn-primary"),
                method="post", action="/invite-clinic",
            ),
            cls="card", style="max-width:720px;",
        )

    if invitations:
        rows = [
            Tr(
                Td(i.get("email", "")),
                Td(i.get("clinic_name") or "—"),
                Td(status_badge(i.get("status", ""), "invitation")),
                Td(fmt_date(i.get("created_at") or "")),
            )
            for i in invitations
        ]
        table = Div(Table(
            Thead(Tr(Th(_("ob.col_email")), Th(_("ob.col_clinic")), Th(_("ob.col_status")), Th(_("ob.col_sent")))),
            Tbody(*rows),
        ), cls="table-wrap")
    else:
        table = P(_("ob.invitations_empty"), cls="ob-muted")

    return Div(
        Style(ONBOARDING_CSS),
        H1(_("ob.invite_clinic")),
        P(_("ob.invite_intro"), style="color:var(--c-text-2);margin-bottom:18px;"),
        form_card,
        Div(H3(_("ob.invitations_heading"), cls="card-title"), table,
            P(_("ob.invitations_hint"), cls="ob-muted", style="margin-top:10px;"),
            cls="card", style="max-width:960px;margin-top:16px;"),
    )


async def _load(token):
    try:
        me = await ob_api.get_me(token)
    except Exception:
        me = {}
    try:
        invitations = await ob_api.my_clinic_invitations(token)
    except Exception:
        invitations = []
    return me, invitations


@rt("/invite-clinic")
async def get(req, sent: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    me, invitations = await _load(token)
    return page_shell(_page(_, me, invitations, sent=sent or None),
                      current="/invite-clinic", title=_("ob.invite_clinic"), lang=lang)


@rt("/invite-clinic")
async def post(req, email: str = "", message: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    email = email.strip()
    error = ""
    if not email:
        error = _("ob.invite_email_required")
    else:
        try:
            await ob_api.invite_clinic(token, email, message.strip())
            from urllib.parse import quote
            return RedirectResponse(f"/invite-clinic?sent={quote(email)}", status_code=303)
        except httpx.HTTPStatusError as e:
            error = _("ob.invite_locked_body") if error_detail(e) == "quests_pending" else _("ob.invite_failed")
        except Exception:
            error = _("ob.invite_failed")
    me, invitations = await _load(token)
    return page_shell(_page(_, me, invitations, error=error, values={"email": email, "message": message}),
                      current="/invite-clinic", title=_("ob.invite_clinic"), lang=lang)
