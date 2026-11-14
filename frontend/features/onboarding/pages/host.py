# pages/host.py — /host, the talk host's page.
#
# Visitors: engineers doing the welcome quests; after a community talk the
# host confirms attendance, which completes the third quest. Shown to
# Community Builders (and superusers).
# Clinics waiting for their clinic talk: the host unlocks them afterwards so
# the clinic can register devices. Shown to Clinics Connectors (and
# superusers). Each section appears only for those who can act on it.

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api
from features.onboarding.ui import ONBOARDING_CSS
from components import page_shell, status_badge, fmt_date, alert
from i18n import t as make_t

rt = APIRouter()


@rt("/host")
async def get(req, ok: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        applicants = await ob_api.host_applicants(token)
    except Exception:
        applicants = None   # not a talk host
    try:
        clinics = await ob_api.host_clinics(token)
    except Exception:
        clinics = None      # not a Clinics Connector
    if applicants is None and clinics is None:
        return RedirectResponse("/home", status_code=302)

    def q(done):
        return status_badge("done" if done else "todo", "quest")

    app_rows = [
        Tr(
            Td(A(a.get("name") or a.get("username", ""), href=f"/profile/{a['id']}"),
               Span(a.get("email", ""), cls="ob-muted", style="display:block;")),
            Td(q(a["quests"].get("complete_profile"))),
            Td(q(a["quests"].get("profile_photo"))),
            Td(q(a["quests"].get("community_talk"))),
            Td(Form(Button(_("ob.host_confirm_talk"), type="submit", cls="btn btn-primary btn-sm"),
                    method="post", action=f"/host/applicants/{a['id']}/talk")
               if not a["quests"].get("community_talk") else ""),
        )
        for a in applicants or []
    ]
    clinic_rows = [
        Tr(
            Td(c.get("name", ""), Span(c.get("address") or "", cls="ob-muted", style="display:block;")),
            Td(c.get("admin_name", ""), Span(c.get("admin_email", ""), cls="ob-muted", style="display:block;")),
            Td(fmt_date(c.get("created_at") or "")),
            Td(Form(Button(_("ob.host_unlock"), type="submit", cls="btn btn-primary btn-sm"),
                    method="post", action=f"/host/clinics/{c['id']}/unlock")),
        )
        for c in clinics or []
    ]
    empty = lambda n, key: Tbody(Tr(Td(_(key), colspan=str(n),
                                       style="text-align:center;padding:20px;color:var(--c-text-3);")))
    content = Div(
        Style(ONBOARDING_CSS),
        H1(_("nav.talk_host")),
        P(_("ob.host_intro"), style="color:var(--c-text-2);margin-bottom:18px;"),
        alert(_("ob.host_done"), "success") if ok else "",
        Div(H3(_("ob.host_visitors"), cls="card-title"),
            Div(Table(Thead(Tr(Th(_("ob.col_engineer")), Th(_("ob.quest_profile")), Th(_("ob.quest_photo")),
                               Th(_("ob.quest_talk")), Th(""))),
                      Tbody(*app_rows) if app_rows else empty(5, "ob.host_no_visitors")), cls="table-wrap"),
            cls="card", style="max-width:1100px;margin-bottom:16px;") if applicants is not None else "",
        Div(H3(_("ob.host_clinics"), cls="card-title"),
            P(_("ob.host_clinics_body"), cls="ob-muted", style="margin-bottom:12px;"),
            Div(Table(Thead(Tr(Th(_("ob.col_clinic")), Th(_("ob.col_contact")), Th(_("ob.col_signed_up")), Th(""))),
                      Tbody(*clinic_rows) if clinic_rows else empty(4, "ob.host_no_clinics")), cls="table-wrap"),
            cls="card", style="max-width:1100px;") if clinics is not None else "",
    )
    return page_shell(content, current="/host", title=_("nav.talk_host"), lang=lang)


@rt("/host/applicants/{profile_id}/talk")
async def post(req, profile_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await ob_api.host_confirm_talk(token, profile_id)
    except Exception:
        return RedirectResponse("/host", status_code=303)
    return RedirectResponse("/host?ok=1", status_code=303)


@rt("/host/clinics/{org_id}/unlock")
async def post(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await ob_api.host_unlock_clinic(token, org_id)
    except Exception:
        return RedirectResponse("/host", status_code=303)
    return RedirectResponse("/host?ok=1", status_code=303)
