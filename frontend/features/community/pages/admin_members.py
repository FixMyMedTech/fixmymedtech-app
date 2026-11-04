# /community/admin/members — members, their teams and achievements.
#
# Who can do what (utils/community.py powers_from):
#   any team member or lead   see members; recognise achievements of their team's category
#   Community Builders        also make anyone a candidate for any team
#   a team's lead             add and remove members of their team
#   superusers                everything, including naming leads

from urllib.parse import quote, urlencode

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import (
    admin_tabs, name_of, stars, flash, error_detail, fmt_dt, country_select, perms,
)
from i18n import t as make_t

rt = APIRouter()

PAGE = 50
LEVELS = ("candidate", "member", "lead")


def can_set(mine: set, team: str, level: str) -> bool:
    """Mirror of Powers.can_add (the backend checks it again)."""
    if level == "lead":
        return "name_leads" in mine
    if level == "member":
        return f"manage_members:{team}" in mine
    return f"set_candidate:{team}" in mine or f"manage_members:{team}" in mine


def _team_pills(places, teams, lang, _):
    active = [t for t in places if t.get("status") == "active"]
    if not active:
        return Span("—", cls="cj-small")
    return Div(*[Span(name_of(teams.get(t["team_key"]), lang) + " · " + _(f"cj.level.{t['level']}"),
                      cls="badge " + ("badge-warn" if t["level"] == "candidate" else "badge-ok"))
                 for t in active], cls="cj-pills")


def _achievement_summary(items, achievements, lang):
    earned = [a for a in items if a.get("level")]
    if not earned:
        return Span("—", cls="cj-small")
    return Div(*[Span(f"{name_of(achievements.get(a['key']), lang)} {a['level']}★", cls="badge badge-neutral")
                 for a in earned], cls="cj-pills")


def _filters(q, team, country, teams, lang, _):
    return Form(
        Div(Label(_("cj.admin.search"), cls="label", for_="q"),
            Input(type="search", id="q", name="q", value=q, cls="input",
                  placeholder=_("cj.admin.search_placeholder")), cls="form-group"),
        Div(Label(_("cj.admin.team"), cls="label", for_="team"),
            Select(Option(_("cj.admin.any_team"), value=""),
                   *[Option(name_of(t, lang), value=k, selected=(k == team)) for k, t in teams.items()],
                   name="team", id="team", cls="input"), cls="form-group"),
        Div(Label(_("cj.admin.country"), cls="label", for_="country"),
            country_select("country", country, _), cls="form-group"),
        Button(_("cj.admin.filter"), type="submit", cls="btn btn-secondary btn-sm", style="align-self:flex-end;"),
        method="get", action="/community/admin/members", cls="cj-row",
    )


def _table(items, sel, query, teams, achievements, lang, _):
    if not items:
        return Div(P(_("cj.admin.no_members")), cls="cj-card")
    rows = [Tr(
        Td(A(m.get("full_name") or m.get("username"), href=f"?{query}&sel={m['id']}", style="font-weight:500;")),
        Td(", ".join(x for x in (m.get("city"), m.get("country")) if x)),
        Td(_team_pills(m.get("teams") or [], teams, lang, _)),
        Td(_achievement_summary(m.get("achievements") or [], achievements, lang)),
        Td(Span(_("cj.paused"), cls="badge badge-neutral") if m.get("paused")
           else fmt_dt(m.get("last_active_at"))[:10]),
        cls="sel" if m["id"] == sel else None,
    ) for m in items]
    heads = ("cj.admin.col_name", "cj.admin.col_place", "cj.admin.col_teams", "cj.admin.col_achievements",
             "cj.admin.col_active")
    return Div(Table(Thead(Tr(*[Th(_(k), scope="col") for k in heads])), Tbody(*rows), cls="cj-table"),
               cls="cj-tablewrap")


def history_line(c: dict, teams: dict, achievements: dict, lang: str, _) -> str:
    """One readable sentence for a community_changes row."""
    data = c.get("after") or c.get("before") or {}
    action = c["action"]
    if action == "member_status":
        detail = _(f"cj.member_status.{(c.get('after') or {}).get('member_status', 'member')}")
    elif action == "quest_confirmed":
        detail = _(f"cj.quest.{data.get('quest', '')}")
    elif action in ("team_added", "team_changed", "team_removed"):
        detail = name_of(teams.get(data.get("team")), lang) or data.get("team", "")
        if data.get("level"):
            detail += " · " + _(f"cj.level.{data['level']}")
    elif action in ("achievement_recognised", "achievement_removed"):
        detail = name_of(achievements.get(data.get("achievement")), lang) or data.get("achievement", "")
        if (data.get("count") or 1) > 1:
            detail += f" ×{data['count']}"
    elif action == "team_edited":
        detail = name_of(teams.get(c.get("target")), lang)
    else:
        detail = ""
    return _(f"cj.history.{action}", action.replace("_", " ")) + (f": {detail}" if detail else "")


def _team_form(m, mine, teams, lang, _):
    current = {t["team_key"]: t["level"] for t in m.get("teams") or [] if t.get("status") == "active"}
    options = [Option(f"{name_of(t, lang)} · {_(f'cj.level.{lvl}')}", value=f"{k}|{lvl}")
               for k, t in teams.items() for lvl in LEVELS
               if can_set(mine, k, lvl) and current.get(k) != lvl
               and (current.get(k) is None or can_set(mine, k, current[k]))]
    if not options or m.get("member_status") != "member":
        return ""
    return Details(
        Summary(_("cj.admin.add_to_team"), style="cursor:pointer;font-weight:500;color:var(--primary);"),
        Form(
            Div(Label(_("cj.admin.team_and_level"), cls="label", for_="team_level"),
                Select(*options, name="team_level", id="team_level", cls="input", required=True),
                Span(_("cj.admin.team_level_help"), cls="cj-small"), cls="form-group"),
            Div(Label(_("cj.admin.reason"), cls="label", for_="t_reason"),
                Textarea(id="t_reason", name="reason", rows="2", cls="input"), cls="form-group"),
            Button(_("cj.admin.add_to_team_confirm"), type="submit", cls="btn btn-primary btn-sm"),
            method="post", action=f"/community/admin/members/{m['id']}/teams",
        ),
    )


def _recognise_form(m, mine, achievements, teams, lang, _):
    options = [Option(f"{name_of(a, lang)} ({name_of(teams.get(a['team_key']), lang)})", value=k)
               for k, a in achievements.items()
               if a["source"] == "recognised" and f"recognise:{a['team_key']}" in mine]
    if not options or m.get("member_status") != "member":
        return ""
    return Details(
        Summary(_("cj.admin.recognise"), style="cursor:pointer;font-weight:500;color:var(--primary);"),
        Form(
            Div(Label(_("cj.admin.achievement"), cls="label", for_="achievement_key"),
                Select(*options, name="achievement_key", id="achievement_key", cls="input", required=True),
                cls="form-group"),
            Div(Label(_("cj.admin.how_many"), cls="label", for_="count"),
                Input(type="number", id="count", name="count", value="1", min="1", max="100", cls="input"),
                Span(_("cj.admin.how_many_help"), cls="cj-small"), cls="form-group"),
            Div(Label(_("cj.admin.note"), cls="label", for_="note"),
                Textarea(id="note", name="note", rows="2", cls="input",
                         placeholder=_("cj.admin.note_placeholder")), cls="form-group"),
            Button(_("cj.admin.recognise_confirm"), type="submit", cls="btn btn-primary btn-sm"),
            method="post", action=f"/community/admin/members/{m['id']}/achievements",
        ),
    )


def _remove_details(label, action, field_id, _):
    return Details(
        Summary(label, style="cursor:pointer;color:var(--danger);font-size:13px;"),
        Form(
            Label(_("cj.admin.remove_reason"), cls="label", for_=field_id),
            Textarea(id=field_id, name="reason", rows="2", cls="input", required=True),
            Button(_("cj.admin.remove_confirm"), type="submit", cls="btn btn-danger btn-sm", style="margin-top:8px;"),
            method="post", action=action,
        ),
    )


def _detail(m, mine, teams, achievements, lang, _):
    place_rows = []
    for t in m.get("teams") or []:
        active = t.get("status") == "active"
        meta = [fmt_dt(t.get("granted_at"))[:10]]
        if t.get("granted_by_name"):
            meta.append(_("cj.admin.by").format(name=t["granted_by_name"]))
        if not active:
            meta.append(_("cj.admin.removed_on").format(date=fmt_dt(t.get("removed_at"))[:10],
                                                        reason=t.get("removed_reason") or "—"))
        remove = _remove_details(_("cj.admin.remove_from_team"),
                                 f"/community/admin/members/{m['id']}/teams/{t['id']}/remove", f"r_{t['id']}", _) \
            if active and can_set(mine, t["team_key"], t["level"]) else ""
        place_rows.append(Div(
            Div(Span(name_of(teams.get(t["team_key"]), lang) + " · " + _(f"cj.level.{t['level']}"),
                     cls="cj-quest-title"),
                Span(" · ".join(x for x in meta if x), cls="cj-small"), remove, cls="cj-quest-body"),
            cls="cj-quest", style=None if active else "opacity:.6;",
        ))

    ach_rows = []
    for p in m.get("achievements") or []:
        a = achievements.get(p["key"])
        if not a:
            continue
        ach_rows.append(Div(
            Div(Div(Span(name_of(a, lang), cls="cj-quest-title"), stars(p.get("level", 0)), cls="cj-between"),
                Span(_("cj.map.unit_devices" if a["source"] == "metric" else "cj.map.unit_times").format(n=p.get("count", 0)),
                     cls="cj-small"),
                cls="cj-quest-body"),
            cls="cj-quest"))

    record_rows = []
    for r in m.get("records") or []:
        a = achievements.get(r["achievement_key"]) or {}
        removable = "name_leads" in mine or f"manage_members:{a.get('team_key')}" in mine
        record_rows.append(Li(
            Span(fmt_dt(r.get("created_at"))[:10], cls="cj-small"), " ",
            name_of(a, lang) + (f" ×{r['count']}" if r.get("count", 1) > 1 else ""),
            Span(f" — {r['recognised_by_name']}", cls="cj-small") if r.get("recognised_by_name") else "",
            Div(Span(f"“{r['note']}”", cls="cj-small")) if r.get("note") else "",
            _remove_details(_("cj.admin.remove_record"),
                            f"/community/admin/members/{m['id']}/records/{r['id']}/remove", f"rr_{r['id']}", _)
            if removable else "",
        ))

    history = m.get("history") or []
    return Div(
        H2(m.get("full_name") or m.get("username")),
        Span(" · ".join(x for x in (", ".join(y for y in (m.get("city"), m.get("country")) if y),
                                    _("cj.journey.member_since").format(date=fmt_dt(m.get("member_since"))[:10])
                                    if m.get("member_since") else "") if x), cls="cj-small"),
        flash(_("cj.admin.member_paused"), "warning") if m.get("paused") else "",
        Dl(
            Dt(_("cj.admin.email")), Dd(A(m["email"], href=f"mailto:{m['email']}") if m.get("email") else "—"),
            Dt(_("cj.admin.why_bme")), Dd(m.get("why_bme") or "—"),
            Dt(_("cj.admin.col_active")), Dd(fmt_dt(m.get("last_active_at"))[:10] or "—"),
            cls="cj-dl",
        ),
        H3(_("cj.admin.col_teams")),
        Div(*place_rows) if place_rows else P(_("cj.journey.no_teams")),
        _team_form(m, mine, teams, lang, _),
        H3(_("cj.admin.col_achievements")),
        Div(*ach_rows),
        _recognise_form(m, mine, achievements, teams, lang, _),
        Details(Summary(_("cj.admin.recognitions").format(n=len(record_rows)), style="cursor:pointer;font-weight:500;"),
                Ul(*record_rows, style="margin:8px 0 0;padding-left:18px;line-height:1.7;"))
        if record_rows else "",
        H3(_("cj.admin.tab_history")),
        Ul(*[Li(Span(fmt_dt(c.get("created_at")), cls="cj-small"), " ",
                history_line(c, teams, achievements, lang, _),
                Span(f" — {c['actor_name']}", cls="cj-small") if c.get("actor_name") else "",
                Div(Span(f"“{c['reason']}”", cls="cj-small")) if c.get("reason") else "")
             for c in history[:30]], style="margin:0;padding-left:18px;line-height:1.7;")
        if history else P(_("cj.admin.no_history")),
        cls="cj-card",
    )


async def load_catalogue():
    try:
        cat = await community_api.get_catalogue()
    except Exception:
        cat = {}
    return ({t["key"]: t for t in cat.get("teams") or []},
            {a["key"]: a for a in cat.get("achievements") or []})


@rt("/community/admin/members")
async def get(req, q: str = "", team: str = "", country: str = "", offset: int = 0, sel: str = "",
              msg: str = "", err: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        data = await community_api.list_members(token, q=q, team=team, country=country, offset=offset)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return RedirectResponse("/community", status_code=302)
        data = {"items": [], "total": 0}
    teams, achievements = await load_catalogue()
    items = data.get("items") or []
    total = data.get("total") or 0
    query = urlencode({k: v for k, v in (("q", q), ("team", team), ("country", country),
                                          ("offset", offset or "")) if v})

    detail = ""
    if sel:
        try:
            member = await community_api.get_member(token, sel)
            detail = _detail(member, set(member.get("can") or []), teams, achievements, lang, _)
        except Exception:
            detail = ""

    pager = ""
    if total > PAGE:
        base = {k: v for k, v in (("q", q), ("team", team), ("country", country)) if v}
        links = []
        if offset > 0:
            links.append(A(_("cj.admin.prev"), href="?" + urlencode({**base, "offset": max(0, offset - PAGE)}),
                           cls="btn btn-secondary btn-sm"))
        if offset + PAGE < total:
            links.append(A(_("cj.admin.next"), href="?" + urlencode({**base, "offset": offset + PAGE}),
                           cls="btn btn-secondary btn-sm"))
        pager = Div(*links, cls="cj-row")

    content = Div(
        Div(H1(_("cj.admin.title")), cls="cj-between"),
        admin_tabs("members", req, _),
        flash(_(f"cj.admin.msg_{msg}", _("cj.saved"))) if msg else "",
        flash(_(f"cj.error.{err}", err), "error") if err else "",
        Div(H2(_("cj.admin.tab_members")), Span(_("cj.admin.total").format(n=total), cls="cj-small"),
            cls="cj-between"),
        _filters(q, team, country, teams, lang, _),
        Div(Div(_table(items, sel, query, teams, achievements, lang, _), pager, cls="wide"),
            Div(detail, cls="side") if detail else "", cls="cj-split"),
        cls="cj",
    )
    return page_shell(content, current="/community/admin", title=_("cj.title.admin"), lang=lang)


def _back(pid, msg="", err=""):
    q = f"sel={pid}"
    if msg:
        q += f"&msg={msg}"
    if err:
        q += f"&err={quote(err)}"
    return RedirectResponse(f"/community/admin/members?{q}", status_code=303)


async def _do(req, pid, call, msg):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await call(token)
    except httpx.HTTPStatusError as e:
        return _back(pid, err=error_detail(e))
    except Exception:
        return _back(pid, err="save")
    return _back(pid, msg=msg)


@rt("/community/admin/members/{pid}/teams")
async def post(req, pid: str):
    form = await req.form()
    team_key, _sep, level = (form.get("team_level") or "").partition("|")
    data = {"team_key": team_key, "level": level or "candidate",
            "reason": (form.get("reason") or "").strip() or None}
    return await _do(req, pid, lambda t: community_api.set_team(t, pid, data), "team_saved")


@rt("/community/admin/members/{pid}/teams/{place_id}/remove")
async def post(req, pid: str, place_id: str):
    form = await req.form()
    reason = (form.get("reason") or "").strip()
    if not reason:
        return _back(pid, err="reason_required")
    return await _do(req, pid, lambda t: community_api.remove_from_team(t, place_id, reason), "team_removed")


@rt("/community/admin/members/{pid}/achievements")
async def post(req, pid: str):
    form = await req.form()
    try:
        count = max(1, min(100, int(form.get("count") or 1)))
    except ValueError:
        count = 1
    data = {"achievement_key": form.get("achievement_key") or "", "count": count,
            "note": (form.get("note") or "").strip() or None}
    return await _do(req, pid, lambda t: community_api.recognise(t, pid, data), "recognised")


@rt("/community/admin/members/{pid}/records/{record_id}/remove")
async def post(req, pid: str, record_id: str):
    form = await req.form()
    reason = (form.get("reason") or "").strip()
    if not reason:
        return _back(pid, err="reason_required")
    return await _do(req, pid, lambda t: community_api.remove_record(t, record_id, reason), "record_removed")
