# /community — My journey: my teams, my achievements with their stars, my counts.

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import hero, name_of, stars, progress_bar, flash, refresh_session, fmt_dt
from i18n import t as make_t

rt = APIRouter()

METRICS = ("devices_registered", "faults_resolved", "maintenance_performed", "invites", "manuals_added")


def achievement_card(ach: dict, p: dict, team: dict, _, lang: str):
    level, count, nxt = p.get("level", 0), p.get("count", 0), p.get("next")
    unit = "cj.map.unit_devices" if ach["source"] == "metric" else "cj.map.unit_times"
    return A(
        Span(name_of(team, lang), cls="cj-eyebrow"),
        Div(H3(name_of(ach, lang)), Span(_("cj.map.level").format(n=level), cls="cj-small"), cls="cj-between"),
        stars(level),
        progress_bar(count - p.get("prev", 0), (nxt - p.get("prev", 0)) if nxt else 1) if nxt else "",
        Span(_(unit).format(n=count) + " · " + (
            _("cj.map.to_next").format(n=nxt - count, level=level + 1) if nxt else _("cj.map.max_level")),
            cls="cj-small"),
        href=f"/community/achievements?sel=ach:{ach['key']}#cj-panel",
        cls="cj-card" + (" is-focus" if level == 0 else ""),
        style="text-decoration:none;color:inherit;",
    )


@rt("/community")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        me = await community_api.get_me(token)
        catalogue = await community_api.get_catalogue()
    except Exception:
        return page_shell(Div(flash(_("cj.error.load"), "error"), cls="cj"), current="/community",
                          title=_("cj.title.journey"), lang=lang)
    if me.get("status_changed"):
        await refresh_session(req, token)
    if me.get("member_status") in ("applicant", "refused"):
        return RedirectResponse("/community/start", status_code=302)

    teams = {t["key"]: t for t in catalogue.get("teams") or []}
    first = (me.get("full_name") or "").split(" ")[0]
    is_member = me.get("member_status") == "member"

    if me.get("member_status") == "staff":
        top = hero(_("cj.journey.staff_title"), _("cj.journey.staff_text"), _("cj.journey.eyebrow"))
    else:
        top = hero(_("cj.journey.title").format(name=first), _("cj.journey.text"), _("cj.journey.eyebrow"))

    my_teams = me.get("teams") or []
    team_block = Div(*[
        A(name_of(teams.get(t["team_key"]), lang) + " · " + _(f"cj.level.{t['level']}")
          + (f" · {_('cj.paused')}" if t.get("paused") else ""),
          href=f"/community/achievements?sel=team:{t['team_key']}#cj-panel",
          cls="badge " + ("badge-neutral" if t.get("paused") else
                          "badge-warn" if t["level"] == "candidate" else "badge-ok"))
        for t in my_teams], cls="cj-pills") if my_teams else P(_("cj.journey.no_teams"))

    progress = {a["key"]: a for a in me.get("achievements") or []}
    cards = [achievement_card(a, progress.get(a["key"], {}), teams.get(a["team_key"]), _, lang)
             for a in catalogue.get("achievements") or []] if is_member else []

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
            A(_("cj.journey.staff_quests_link"), href="/community/start/quests", cls="btn btn-primary btn-sm",
              style="align-self:flex-start;"),
            cls="cj-card is-focus",
        )

    content = Div(
        top,
        flash(_("cj.journey.paused"), "warning") if me.get("paused") and my_teams else "",
        staff_quests,
        Div(Div(H2(_("cj.journey.my_teams")),
                Span(_("cj.journey.member_since").format(date=fmt_dt(me.get("member_since"))[:10]), cls="cj-small")
                if me.get("member_since") else "", cls="cj-between"),
            team_block,
            P(_("cj.journey.teams_help")) if not my_teams else "",
            cls="cj-card"),
        Div(H2(_("cj.journey.my_achievements")),
            A(_("cj.journey.tree_link"), href="/community/achievements", cls="btn btn-secondary btn-sm"),
            cls="cj-between") if cards else "",
        Div(*cards, cls="cj-grid") if cards else "",
        stats,
        cls="cj",
    )
    return page_shell(content, current="/community", title=_("cj.title.journey"), lang=lang)
