# /community/achievements — the achievements map: hexagon tiles for becoming a
# member, the three teams and their achievements, with the selected tile's
# details beside the map. Public: visitors see what they could do; members
# see their teams and star levels.

from urllib.parse import quote

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell, pub_shell
from features.community.ui import (
    name_of, text_of, tasks_of, stars, progress_bar, flash, hex_map, fmt_dt,
)
from i18n import t as make_t

rt = APIRouter()


def build_tiles(catalogue: dict, me: dict | None, _, lang: str) -> dict:
    """{tile key: {"name", "sub", "state", "level", "kind"}} for hex_map."""
    status = (me or {}).get("member_status")
    is_member = status == "member"
    tiles = {"member": {
        "name": _("cj.map.member"), "kind": "start",
        "sub": _("cj.map.member_sub"),
        "state": "" if me is None else ("done" if is_member else "now"),
    }}
    my_teams = {t["team_key"]: t["level"] for t in (me or {}).get("teams") or []}
    for team in catalogue.get("teams") or []:
        level = my_teams.get(team["key"])
        state = "" if me is None else (
            "done" if level in ("member", "lead") else "now" if level == "candidate" else "next")
        tiles[f"team:{team['key']}"] = {
            "name": name_of(team, lang), "kind": "team", "state": state,
            "sub": _(f"cj.level.{level}") if level else _("cj.map.team"),
        }
    progress = {a["key"]: a for a in (me or {}).get("achievements") or []}
    for ach in catalogue.get("achievements") or []:
        p = progress.get(ach["key"])
        if me is None:
            state, level = "", None
        elif not is_member:
            state, level = "next", None
        else:
            level = (p or {}).get("level", 0)
            state = "done" if level else "now"
        tiles[f"ach:{ach['key']}"] = {
            "name": name_of(ach, lang), "kind": "ach", "state": state, "level": level,
            "sub": _("cj.map.achievement"),
        }
    return tiles


def default_selection(tiles: dict) -> str:
    if tiles["member"]["state"] in ("", "now"):
        return "member"
    for key, t in tiles.items():
        if key.startswith("ach:") and t["state"] == "now":
            return key
    return "member"


def _member_panel(me, _):
    if me is None:
        return Div(
            Span(_("cj.map.step"), cls="cj-eyebrow"), H2(_("cj.map.member")),
            P(_("cj.map.member_text")),
            A(_("cj.tree.join_button"), href="/join", cls="btn btn-primary", style="align-self:flex-start;"),
            cls="cj-card", id="cj-panel")
    if me.get("member_status") == "member":
        since = fmt_dt(me.get("member_since"))[:10]
        return Div(
            Span(_("cj.map.step"), cls="cj-eyebrow"), H2(_("cj.map.member")),
            Span(_("cj.state.done"), cls="badge badge-ok", style="align-self:flex-start;"),
            P(_("cj.journey.member_since").format(date=since) if since else _("cj.start.member_text")),
            P(_("cj.map.member_next")),
            cls="cj-card", id="cj-panel")
    quests = me.get("welcome_quests") or []
    done = sum(1 for q in quests if q.get("done"))
    return Div(
        Span(_("cj.map.step"), cls="cj-eyebrow"), H2(_("cj.map.member")),
        P(_("cj.map.member_text")),
        progress_bar(done, len(quests) or 5),
        Span(_("cj.start.progress").format(done=done, total=len(quests) or 5), cls="cj-small"),
        A(_("cj.map.continue_quests"), href="/community/start/quests", cls="btn btn-primary",
          style="align-self:flex-start;"),
        cls="cj-card is-focus", id="cj-panel")


def _team_panel(team, catalogue, me, _, lang):
    my_level = next((t["level"] for t in (me or {}).get("teams") or [] if t["team_key"] == team["key"]), None)
    counts = team.get("counts") or {}
    achievements = [a for a in catalogue.get("achievements") or [] if a["team_key"] == team["key"]]
    linkedin = text_of(team, "linkedin_titles", lang)
    return Div(
        Span(_("cj.map.team"), cls="cj-eyebrow"),
        Div(H2(name_of(team, lang)),
            Span(_(f"cj.level.{my_level}"), cls="badge " + ("badge-warn" if my_level == "candidate" else "badge-ok"))
            if my_level else "", cls="cj-between"),
        P(text_of(team, "descriptions", lang)),
        Ul(*[Li(line) for line in tasks_of(team, lang)],
           style="margin:0;padding-left:20px;color:var(--text);line-height:1.7;font-size:14px;")
        if tasks_of(team, lang) else "",
        Span(_("cj.map.team_counts").format(members=counts.get("member", 0) + counts.get("lead", 0),
                                            candidates=counts.get("candidate", 0)), cls="cj-small"),
        Div(H3(_("cj.map.team_achievements")),
            Div(*[A(name_of(a, lang), href=f"?sel=ach:{a['key']}#cj-panel", cls="badge badge-neutral")
                  for a in achievements], cls="cj-pills")
            if achievements else P(_("cj.map.team_no_achievements"))),
        Div(H3(_("cj.role.linkedin")), P(linkedin, style="color:var(--text);font-weight:500;"),
            Span(_("cj.role.linkedin_help"), cls="cj-small"))
        if linkedin and my_level in ("member", "lead") else "",
        P(_("cj.map.how_to_join")) if not my_level else
        (P(_("cj.map.candidate_text")) if my_level == "candidate" else ""),
        cls="cj-card", id="cj-panel")


def _achievement_panel(ach, catalogue, me, _, lang):
    team = next((t for t in catalogue.get("teams") or [] if t["key"] == ach["team_key"]), {})
    p = next((a for a in (me or {}).get("achievements") or [] if a["key"] == ach["key"]), None)
    is_member = (me or {}).get("member_status") == "member"
    levels = ach.get("levels") or []
    level = (p or {}).get("level", 0)
    count = (p or {}).get("count", 0)
    unit = "cj.map.unit_devices" if ach["source"] == "metric" else "cj.map.unit_times"
    progress = ""
    if p and is_member:
        nxt = p.get("next")
        progress = Div(
            Div(stars(level), Span(_("cj.map.level").format(n=level), cls="cj-small"), cls="cj-between"),
            progress_bar(count - p.get("prev", 0), (nxt - p.get("prev", 0)) if nxt else 1) if nxt else "",
            Span(_(unit).format(n=count) + " · " + (
                _("cj.map.to_next").format(n=nxt - count, level=level + 1) if nxt else _("cj.map.max_level")),
                cls="cj-small"),
            style="display:flex;flex-direction:column;gap:8px;")
    how = _("cj.map.counted_auto") if ach["source"] == "metric" else \
        _("cj.map.recognised_by").format(team=name_of(team, lang))
    return Div(
        Span(_("cj.map.achievement") + " · " + name_of(team, lang), cls="cj-eyebrow"),
        H2(name_of(ach, lang)),
        P(text_of(ach, "descriptions", lang)),
        progress,
        H3(_("cj.map.levels")),
        Div(*[Span(f"{'★' * 1} {i + 1} · {n}", cls="on" if i < level else None,
                   title=_("cj.map.level_needs").format(level=i + 1, n=n))
              for i, n in enumerate(levels)], cls="cj-levels"),
        Span(_("cj.map.levels_help"), cls="cj-small"),
        P(how),
        Span(_("cj.map.earners").format(n=ach.get("earners", 0)), cls="cj-small")
        if ach["source"] != "metric" else "",
        cls="cj-card", id="cj-panel")


@rt("/community/achievements")
async def get(req, sel: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    token = auth_helper.get_token(req)
    try:
        catalogue = await community_api.get_catalogue()
    except Exception:
        catalogue = {}
    me = None
    if token:
        try:
            me = await community_api.get_me(token)
        except Exception:
            me = None
    if not catalogue.get("teams"):
        content = Div(flash(_("cj.error.load"), "error"), cls="cj")
    else:
        tiles = build_tiles(catalogue, me, _, lang)
        sel = sel if sel in tiles else default_selection(tiles)
        if sel == "member":
            panel = _member_panel(me, _)
        elif sel.startswith("team:"):
            team = next(t for t in catalogue["teams"] if f"team:{t['key']}" == sel)
            panel = _team_panel(team, catalogue, me, _, lang)
        else:
            ach = next(a for a in catalogue["achievements"] if f"ach:{a['key']}" == sel)
            panel = _achievement_panel(ach, catalogue, me, _, lang)
        legend = Div(*[Span(I(cls=k), _(f"cj.legend.{k}")) for k in ("done", "now", "next", "fog")],
                     cls="cj-legend")
        content = Div(
            Div(H1(_("cj.tree.title")), P(_("cj.tree.intro")), cls="cj-card"),
            Div(
                Div(legend, hex_map(tiles, sel, lambda k: f"?sel={quote(k)}#cj-panel", _("cj.tree.title")),
                    cls="cj-card", style="gap:var(--space-4);"),
                panel,
                cls="cj-mapsplit",
            ),
            cls="cj",
        )
    if token:
        return page_shell(content, current="/community/achievements", title=_("cj.title.tree"), lang=lang)
    return pub_shell(content, title=_("cj.title.tree"), lang=lang)


# Old addresses from the first version (skill tree and role pages).
@rt("/community/tree")
async def get(req):
    return RedirectResponse("/community/achievements", status_code=301)


@rt("/community/roles/{key}")
async def get(req, key: str):
    return RedirectResponse("/community/achievements", status_code=301)
