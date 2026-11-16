# pages/clinic_engineers.py — /groups/{org_id}/engineers, the clinic page's
# Engineers tab (clinic admins): responsible engineers with their status, the
# inviting engineer, confirm a "not now" engineer later, add (internal or
# external, by email) and remove. Devices an engineer registered stay with the
# clinic when the engineer is removed.

from urllib.parse import quote

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api
from features.onboarding.ui import ONBOARDING_CSS, clinic_tabs
from features.onboarding.pages.clinic_setup import add_engineer_form
from components import page_shell, status_badge, alert
from i18n import t as make_t

rt = APIRouter()


def _row(_, org_id, e):
    actions = []
    if e.get("answer") != "confirmed":
        actions.append(Form(Button(_("ob.confirm_btn"), type="submit", cls="btn btn-primary btn-sm"),
                            method="post", action=f"/groups/{org_id}/engineers/{e['id']}/confirm"))
    actions.append(Form(Button(_("ob.remove_btn"), type="submit", cls="btn btn-danger btn-sm"),
                        method="post", action=f"/groups/{org_id}/engineers/{e['id']}/remove",
                        onsubmit=f"return confirm({_js_str(_('ob.remove_confirm'))});"))
    who = [A(e.get("name") or e.get("email", ""), href=f"/profile/{e['id']}")]
    if e.get("is_inviter"):
        who.append(Span(_("ob.invited_your_clinic"), cls="ob-muted", style="display:block;"))
    quests = ""
    if e.get("status") == "waiting_quests":
        quests = Span(_("ob.quests_count").format(done=e.get("quests_done", 0), total=e.get("quests_total", 3)),
                      cls="ob-muted", style="display:block;")
    return Tr(
        Td(*who),
        Td(_(f"ob.kind_{e.get('kind') or 'external'}")),
        Td(status_badge(e.get("status", ""), "engineer"), quests),
        Td(Div(*actions, cls="ob-actions", style="justify-content:flex-end;")),
    )


def _js_str(value: str) -> str:
    import json
    return json.dumps(value).replace("<", "\\u003c").replace("'", "\\u0027")


@rt("/groups/{org_id}/engineers")
async def get(req, org_id: str, added: str = "", invited: str = "", error: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        data = await ob_api.clinic_engineers(token, org_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404, 400):
            return RedirectResponse("/groups", status_code=302)
        raise
    clinic = data.get("clinic", {})
    engineers = data.get("engineers", [])
    invitations = data.get("invitations", [])
    booking = (data.get("links") or {}).get("clinic_talk_booking") or ""

    talk_notice = Div(
        H3(_("ob.talk_heading"), cls="card-title"),
        P(_("ob.talk_locked")),
        (A(_("ob.talk_book"), href=booking, target="_blank", rel="noopener", cls="btn btn-primary btn-sm")
         if booking else P(_("ob.talk_no_link"), cls="ob-muted")),
        cls="card ob-locked", style="max-width:960px;margin-bottom:16px;",
    ) if clinic.get("clinic_status") == "talk_pending" else ""

    table = Div(Table(
        Thead(Tr(Th(_("ob.col_engineer")), Th(_("ob.col_kind")), Th(_("ob.col_status")),
                 Th(_("groups.member_action"), style="text-align:right;"))),
        Tbody(*[_row(_, org_id, e) for e in engineers]) if engineers else Tbody(
            Tr(Td(_("ob.no_engineers"), colspan="4", style="text-align:center;padding:20px;color:var(--c-text-3);"))),
    ), cls="table-wrap")

    pending = Div(
        H3(_("ob.pending_invitations"), cls="card-title"),
        Ul(*[Li(Span(i["email"], " · ", _(f"ob.kind_{i.get('kind') or 'external'}"), cls="ob-muted"),
                Form(Button(_("ob.cancel_btn"), type="submit", cls="btn btn-secondary btn-sm"),
                     method="post", action=f"/groups/{org_id}/engineers/invitations/{i['id']}/cancel"))
             for i in invitations], cls="ob-list"),
        cls="card", style="max-width:960px;margin-top:16px;",
    ) if invitations else ""

    content = Div(
        Style(ONBOARDING_CSS),
        A(_("groups.back_to_groups"), href="/groups",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:inline-block;margin-bottom:16px;"),
        H1(clinic.get("name", "")),
        clinic_tabs(org_id, "engineers", _),
        alert(_("ob.engineer_added").format(email=added), "success") if added else "",
        alert(_("ob.engineer_invited").format(email=invited), "success") if invited else "",
        alert(_("ob.engineer_add_failed"), "error") if error else "",
        talk_notice,
        Div(H3(_("ob.engineers_heading"), cls="card-title"),
            P(_("ob.engineers_body"), cls="ob-muted", style="margin-bottom:12px;"),
            table, cls="card", style="max-width:960px;"),
        pending,
        Div(H3(_("ob.add_engineer_heading"), cls="card-title"),
            P(_("ob.add_engineer_body"), cls="ob-muted"),
            add_engineer_form(_, f"/groups/{org_id}/engineers/add"),
            cls="card", style="max-width:960px;margin-top:16px;"),
    )
    return page_shell(content, current="/groups", title=clinic.get("name", ""), lang=lang)


async def _act(req, org_id, call):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await call(token)
    except Exception:
        return RedirectResponse(f"/groups/{org_id}/engineers?error=1", status_code=303)
    return RedirectResponse(f"/groups/{org_id}/engineers", status_code=303)


@rt("/groups/{org_id}/engineers/{engineer_id}/confirm")
async def post(req, org_id: str, engineer_id: str):
    return await _act(req, org_id, lambda t: ob_api.confirm_engineer(t, org_id, engineer_id))


@rt("/groups/{org_id}/engineers/{engineer_id}/remove")
async def post(req, org_id: str, engineer_id: str):
    return await _act(req, org_id, lambda t: ob_api.remove_engineer(t, org_id, engineer_id))


@rt("/groups/{org_id}/engineers/invitations/{invitation_id}/cancel")
async def post(req, org_id: str, invitation_id: str):
    return await _act(req, org_id, lambda t: ob_api.cancel_engineer_invitation(t, org_id, invitation_id))


@rt("/groups/{org_id}/engineers/add")
async def post(req, org_id: str, email: str = "", kind: str = "external"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    email = email.strip()
    try:
        res = await ob_api.add_engineer(token, org_id, email, kind)
    except Exception:
        return RedirectResponse(f"/groups/{org_id}/engineers?error=1", status_code=303)
    key = "invited" if res.get("result") == "invited" else "added"
    return RedirectResponse(f"/groups/{org_id}/engineers?{key}={quote(email)}", status_code=303)
