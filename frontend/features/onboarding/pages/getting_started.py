# pages/getting_started.py — /getting-started
#
# What an engineer does once the three welcome quests are done (the "next
# step" card of the brief): invite a clinic, register a device, and the
# clinics that named this engineer. The quests themselves are on
# /community/start/quests (features/community), so an applicant is sent
# there. Re-reads /api/auth/me so the session (sidebar, page gate) follows a
# talk confirmed by a host in the meantime.

import asyncio

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api
from features.onboarding.ui import ONBOARDING_CSS, progress, quest_row
from components import page_shell, status_badge
from i18n import t as make_t

rt = APIRouter()


def _quest_rows(me, quests, _):
    q = {x["key"]: x for x in quests}
    booking = (me.get("links") or {}).get("community_talk_booking") or ""
    missing = q.get("complete_profile", {}).get("missing") or []
    missing_txt = ", ".join(_(f"ob.field_{f}") for f in missing)
    profile_desc = _("ob.quest_profile_desc")
    if missing_txt:
        profile_desc += " " + _("ob.quest_profile_missing").format(fields=missing_txt)
    talk_action = (A(_("ob.quest_talk_book"), href=booking, target="_blank", rel="noopener",
                     cls="btn btn-primary btn-sm")
                   if booking else Span(_("ob.quest_talk_no_link"), cls="ob-muted"))
    return [
        quest_row(1, q.get("complete_profile", {}).get("done"), _("ob.quest_profile"), profile_desc,
                  A(_("ob.quest_profile_cta"), href="/profile", cls="btn btn-primary btn-sm")),
        quest_row(2, q.get("profile_photo", {}).get("done"), _("ob.quest_photo"), _("ob.quest_photo_desc"),
                  A(_("ob.quest_photo_cta"), href="/profile", cls="btn btn-primary btn-sm")),
        quest_row(3, q.get("community_talk", {}).get("done"), _("ob.quest_talk"), _("ob.quest_talk_desc"),
                  talk_action),
    ]


def _clinics_card(clinics, _):
    if not clinics:
        body = P(_("ob.my_clinics_empty"), cls="ob-muted")
    else:
        body = Ul(*[
            Li(Span(c.get("name", "")), status_badge(c.get("status", ""), "engineer"))
            for c in clinics
        ], cls="ob-list")
    return Div(H3(_("ob.my_clinics"), cls="card-title"), body, cls="card",
               style="max-width:720px;margin-top:16px;")


@rt("/getting-started")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    # /api/onboarding/me first: it promotes an applicant whose quests are all
    # done, and the session refresh after it then sees the new status.
    try:
        me, clinics = await asyncio.gather(ob_api.get_me(token), ob_api.my_clinics(token))
    except Exception:
        me, clinics = {}, []
    user = await auth_helper.refresh_onboarding(req, token)
    if user.get("account_kind") == "clinic":
        return RedirectResponse("/clinic/setup", status_code=302)
    if user.get("member_status") in ("applicant", "refused"):
        return RedirectResponse("/community/start/quests", status_code=302)

    quests = me.get("quests") or []
    done, total = me.get("quests_done", 0), me.get("quests_total", 3)
    unlocked = bool(me.get("is_unlocked"))

    if unlocked:
        top = Div(
            H3(_("ob.done_heading"), cls="card-title"),
            P(_("ob.done_body")),
            Div(A(_("ob.invite_clinic_cta"), href="/invite-clinic", cls="btn btn-primary"),
                A(_("ob.register_device_cta"), href="/new_device", cls="btn btn-secondary"),
                cls="ob-actions"),
            cls="card ob-next", style="max-width:720px;",
        )
        content = Div(
            Style(ONBOARDING_CSS),
            H1(_("ob.getting_started")),
            P(_("ob.intro_done"), style="color:var(--c-text-2);margin-bottom:18px;"),
            top,
            _clinics_card(clinics, _),
        )
    else:
        content = Div(
            Style(ONBOARDING_CSS),
            H1(_("ob.getting_started")),
            P(_("ob.intro"), style="color:var(--c-text-2);margin-bottom:18px;"),
            Div(
                H3(_("ob.quests_heading"), cls="card-title"),
                progress(done, total, _),
                *_quest_rows(me, quests, _),
                cls="card", style="max-width:720px;",
            ),
            Div(
                H3(_("ob.next_heading"), cls="card-title"),
                P(_("ob.next_body")),
                cls="card ob-locked", style="max-width:720px;margin-top:16px;",
            ),
            _clinics_card(clinics, _) if clinics else "",
        )
    return page_shell(content, current="/getting-started", title=_("ob.getting_started"), lang=lang)
