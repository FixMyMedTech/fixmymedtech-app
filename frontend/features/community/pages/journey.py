# /community — My journey: my roles, my next unlocks with progress, my counts.

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import (
    hero, role_name, place, progress_bar, requirement_list, flash, refresh_session, fmt_dt,
)
from i18n import t as make_t

rt = APIRouter()

METRICS = ("devices_registered", "faults_resolved", "maintenance_performed", "invites", "manuals_added")


@rt("/community")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        me = await community_api.get_me(token)
        tree = await community_api.get_tree()
    except Exception:
        return page_shell(Div(flash(_("cj.error.load"), "error"), cls="cj"), current="/community",
                          title=_("cj.title.journey"), lang=lang)
    if me.get("status_changed") or me.get("new_roles"):
        await refresh_session(req, token)
    if me.get("member_status") in ("applicant", "refused"):
        return RedirectResponse("/community/start", status_code=302)

    roles_by_key = {r["key"]: r for r in tree.get("roles") or []}
    first = (me.get("full_name") or "").split(" ")[0]
    held = [h for h in me.get("roles") or [] if h.get("status") == "active"]

    new_roles = me.get("new_roles") or []
    notices = [flash(_("cj.journey.unlocked").format(role=role_name(roles_by_key.get(k), lang))) for k in new_roles]
    if me.get("paused"):
        notices.append(flash(_("cj.journey.paused"), "warning"))

    if me.get("member_status") == "staff":
        top = hero(_("cj.journey.staff_title"), _("cj.journey.staff_text"), _("cj.journey.eyebrow"))
    else:
        top = hero(_("cj.journey.title").format(name=first), _("cj.journey.text"), _("cj.journey.eyebrow"))

    role_badges = Div(
        *[A(role_name(roles_by_key.get(h["role_key"], {"names": h.get("names")}), lang)
            + (f" · {place(h, _)}" if place(h, _) else "")
            + (f" · {_('cj.paused')}" if h.get("paused") else ""),
            href=f"/community/roles/{h['role_key']}",
            cls="badge " + ("badge-neutral" if h.get("paused") else "badge-ok"))
          for h in held],
        cls="cj-pills",
    ) if held else P(_("cj.journey.no_roles"))

    next_cards = []
    for n in me.get("next_unlocks") or []:
        role = roles_by_key.get(n["key"], {})
        action = A(_("cj.journey.see_role"), href=f"/community/roles/{n['key']}", cls="btn btn-secondary btn-sm")
        if n.get("ready") and n.get("unlock") == "claim":
            action = A(_("cj.journey.claim"), href=f"/community/roles/{n['key']}", cls="btn btn-primary btn-sm")
        next_cards.append(Div(
            Span(_("cj.journey.next_unlock"), cls="cj-eyebrow"),
            H3(role_name(role, lang)),
            progress_bar(n["met"], n["total"]),
            Span(_("cj.role.progress").format(met=n["met"], total=n["total"]), cls="cj-small"),
            requirement_list(n.get("requirements") or [], roles_by_key, _, lang),
            Div(action, cls="cj-row"),
            cls="cj-card" + (" is-focus" if n.get("ready") else ""),
        ))

    metrics = me.get("metrics") or {}
    stats = Div(
        *[Div(Div(str(metrics.get(m, 0)), style="font-size:24px;font-weight:700;color:var(--text);"),
              Span(_(f"cj.count.{m}"), cls="cj-small"),
              style="display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;min-width:90px;")
          for m in METRICS],
        cls="cj-card", style="flex-direction:row;flex-wrap:wrap;",
    )

    staff_quests = ""
    if me.get("member_status") == "staff":
        done = sum(1 for q in me.get("welcome_quests") or [] if q.get("done"))
        staff_quests = Div(
            H3(_("cj.journey.staff_quests")),
            progress_bar(done, 5),
            P(_("cj.start.progress").format(done=done, total=5)),
            A(_("cj.journey.staff_quests_link"), href="/community/start", cls="btn btn-primary btn-sm",
              style="align-self:flex-start;"),
            cls="cj-card is-focus",
        )

    content = Div(
        top,
        *notices,
        staff_quests,
        Div(Div(H2(_("cj.journey.my_roles")),
                Span(_("cj.journey.member_since").format(date=fmt_dt(me.get("member_since"))[:10]), cls="cj-small")
                if me.get("member_since") else "", cls="cj-between"),
            role_badges, cls="cj-card"),
        Div(*next_cards, cls="cj-grid") if next_cards else "",
        stats,
        Div(
            P(_("cj.journey.tree_text")),
            A(_("cj.journey.tree_link"), href="/community/tree", cls="btn btn-secondary btn-sm",
              style="align-self:flex-start;"),
            cls="cj-card",
        ),
        cls="cj",
    )
    return page_shell(content, current="/community", title=_("cj.title.journey"), lang=lang)
