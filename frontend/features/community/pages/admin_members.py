# /community/admin/members — members in your scope, their roles and counts.
#
# Who sees what (permissions from utils/community.py):
#   view_members   see the list and a member's roles, counts and history
#   assign_roles   add a role to a member, or remove one (a reason is required)

from urllib.parse import quote, urlencode

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import (
    admin_tabs, role_name, place, flash, error_detail, fmt_dt, country_select,
)
from i18n import t as make_t

rt = APIRouter()

PAGE = 50
METRICS = ("devices_registered", "faults_resolved", "maintenance_performed", "invites", "manuals_added")


def _role_pills(roles, roles_by_key, lang, _):
    active = [h for h in roles if h.get("status") == "active"]
    if not active:
        return Span("—", cls="cj-small")
    return Div(*[Span(role_name(roles_by_key.get(h["role_key"], {"names": h.get("names")}), lang)
                      + (f" · {place(h, _)}" if place(h, _) else ""),
                      cls="badge " + ("badge-neutral" if h.get("paused") else "badge-ok"))
                 for h in active], cls="cj-pills")


def _filters(q, role, country, roles, lang, _):
    return Form(
        Div(Label(_("cj.admin.search"), cls="label", for_="q"),
            Input(type="search", id="q", name="q", value=q, cls="input",
                  placeholder=_("cj.admin.search_placeholder")), cls="form-group"),
        Div(Label(_("cj.admin.col_roles"), cls="label", for_="role"),
            Select(Option(_("cj.admin.any_role"), value=""),
                   *[Option(role_name(r, lang), value=r["key"], selected=(r["key"] == role)) for r in roles],
                   name="role", id="role", cls="input"), cls="form-group"),
        Div(Label(_("cj.admin.country"), cls="label", for_="country"),
            country_select("country", country, _), cls="form-group"),
        Button(_("cj.admin.filter"), type="submit", cls="btn btn-secondary btn-sm", style="align-self:flex-end;"),
        method="get", action="/community/admin/members", cls="cj-row",
    )


def _table(items, sel, query, roles_by_key, lang, _):
    if not items:
        return Div(P(_("cj.admin.no_members")), cls="cj-card")
    rows = []
    for m in items:
        rows.append(Tr(
            Td(A(m.get("full_name") or m.get("username"), href=f"?{query}&sel={m['id']}", style="font-weight:500;")),
            Td(", ".join(x for x in (m.get("city"), m.get("country")) if x)),
            Td(_role_pills(m.get("roles") or [], roles_by_key, lang, _)),
            Td(str(m.get("devices_registered", 0)), cls="n"),
            Td(str(m.get("faults_resolved", 0) + m.get("maintenance_performed", 0)), cls="n"),
            Td(str(m.get("invites", 0)), cls="n"),
            Td(Span(_("cj.paused"), cls="badge badge-neutral") if m.get("paused")
               else fmt_dt(m.get("last_active_at"))[:10]),
            cls="sel" if m["id"] == sel else None,
        ))
    heads = (("cj.admin.col_name", None), ("cj.admin.col_place", None), ("cj.admin.col_roles", None),
             ("cj.admin.col_devices", "n"), ("cj.admin.col_repairs", "n"), ("cj.admin.col_invites", "n"),
             ("cj.admin.col_active", None))
    return Div(Table(Thead(Tr(*[Th(_(k), scope="col", cls=c) for k, c in heads])), Tbody(*rows),
                     cls="cj-table"), cls="cj-tablewrap")


def history_line(c: dict, roles_by_key: dict, lang: str, _) -> str:
    """One readable sentence for a community_role_changes row."""
    data = c.get("after") or c.get("before") or {}
    role = role_name(roles_by_key.get(data.get("role")), lang) if data.get("role") else ""
    where = _(f"cj.team.{data['team']}") if data.get("team") else (data.get("country") or "")
    if c["action"] == "member_status":
        detail = _(f"cj.member_status.{(c.get('after') or {}).get('member_status', 'member')}")
    elif c["action"] == "quest_confirmed":
        detail = _(f"cj.quest.{data.get('quest', '')}")
    else:
        detail = role + (f" · {where}" if where and role else "")
    return _(f"cj.history.{c['action']}", c["action"]) + (f": {detail}" if detail else "")


def _assign_form(m, roles, teams, lang, _):
    return Details(
        Summary(_("cj.admin.add_role"), style="cursor:pointer;font-weight:500;color:var(--brand-primary);"),
        Form(
            Div(Label(_("cj.admin.role"), cls="label", for_="role_key"),
                Select(*[Option(role_name(r, lang), value=r["key"]) for r in roles],
                       name="role_key", id="role_key", cls="input", required=True), cls="form-group"),
            Div(Label(_("cj.admin.country"), cls="label", for_="a_country"),
                country_select("country", m.get("country") or "", _, id="a_country"),
                Span(_("cj.admin.country_help"), cls="cj-small"), cls="form-group"),
            Div(Label(_("cj.admin.team"), cls="label", for_="team"),
                Select(Option("—", value=""), *[Option(_(f"cj.team.{t}"), value=t) for t in teams],
                       name="team", id="team", cls="input"),
                Span(_("cj.admin.team_help"), cls="cj-small"), cls="form-group"),
            Div(Label(_("cj.admin.reason"), cls="label", for_="a_reason"),
                Textarea(id="a_reason", name="reason", rows="2", cls="input"), cls="form-group"),
            Button(_("cj.admin.add_role_confirm"), type="submit", cls="btn btn-primary btn-sm"),
            method="post", action=f"/community/admin/members/{m['id']}/roles",
        ),
    )


def _detail(m, roles_by_key, teams, lang, _):
    can_assign = m.get("can_assign")
    role_rows = []
    for h in m.get("roles") or []:
        active = h.get("status") == "active"
        name = role_name(roles_by_key.get(h["role_key"], {"names": h.get("names")}), lang)
        where = place(h, _)
        meta = [_(f"cj.source.{h.get('source') or 'auto'}"), fmt_dt(h.get("granted_at"))[:10]]
        if h.get("granted_by_name"):
            meta.append(_("cj.admin.by").format(name=h["granted_by_name"]))
        if not active:
            meta.append(_("cj.admin.removed_on").format(date=fmt_dt(h.get("removed_at"))[:10],
                                                        reason=h.get("removed_reason") or "—"))
        remove = ""
        if can_assign and active:
            remove = Details(
                Summary(_("cj.admin.remove_role"), style="cursor:pointer;color:var(--danger);font-size:13px;"),
                Form(
                    Label(_("cj.admin.remove_reason"), cls="label", for_=f"r_{h['id']}"),
                    Textarea(id=f"r_{h['id']}", name="reason", rows="2", cls="input", required=True),
                    Button(_("cj.admin.remove_confirm"), type="submit", cls="btn btn-danger btn-sm",
                           style="margin-top:8px;"),
                    method="post", action=f"/community/admin/members/{m['id']}/roles/{h['id']}/remove",
                ),
            )
        role_rows.append(Div(
            Div(Span(name + (f" · {where}" if where else ""), cls="cj-quest-title"),
                Span(" · ".join(x for x in meta if x), cls="cj-small"), remove, cls="cj-quest-body"),
            cls="cj-quest" + ("" if active else " is-removed"),
            style=None if active else "opacity:.6;",
        ))

    metrics = m.get("metrics") or {}
    history = m.get("history") or []
    assignable = sorted((r for r in roles_by_key.values() if r["key"] != "ambassador"),
                        key=lambda r: (r["path"], r["tier"], r["sort"]))
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
            *[x for k in METRICS for x in (Dt(_(f"cj.count.{k}")), Dd(str(metrics.get(k, 0))))],
            cls="cj-dl",
        ),
        H3(_("cj.admin.col_roles")),
        Div(*role_rows) if role_rows else P(_("cj.journey.no_roles")),
        _assign_form(m, assignable, teams, lang, _) if can_assign and m.get("member_status") == "member" else "",
        H3(_("cj.admin.tab_history")),
        Ul(*[Li(Span(fmt_dt(c.get("created_at")), cls="cj-small"), " ",
                history_line(c, roles_by_key, lang, _),
                Span(f" — {c['actor_name']}", cls="cj-small") if c.get("actor_name") else "",
                Div(Span(f"“{c['reason']}”", cls="cj-small")) if c.get("reason") else "")
             for c in history[:30]], style="margin:0;padding-left:18px;line-height:1.7;")
        if history else P(_("cj.admin.no_history")),
        cls="cj-card",
    )


@rt("/community/admin/members")
async def get(req, q: str = "", role: str = "", country: str = "", offset: int = 0, sel: str = "",
              msg: str = "", err: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        data = await community_api.list_members(token, q=q, role=role, country=country, offset=offset)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return RedirectResponse("/community", status_code=302)
        data = {"items": [], "total": 0, "scope": {}}
    try:
        tree = await community_api.get_tree()
    except Exception:
        tree = {"roles": [], "teams": []}
    roles = sorted(tree.get("roles") or [], key=lambda r: (r["path"], r["tier"], r["sort"]))
    roles_by_key = {r["key"]: r for r in roles}
    items = data.get("items") or []
    total = data.get("total") or 0
    scope = data.get("scope") or {}
    query = urlencode({k: v for k, v in (("q", q), ("role", role), ("country", country),
                                          ("offset", offset or "")) if v})

    detail = ""
    if sel:
        try:
            detail = _detail(await community_api.get_member(token, sel), roles_by_key, tree.get("teams") or [],
                             lang, _)
        except Exception:
            detail = ""

    pager = ""
    if total > PAGE:
        base = {k: v for k, v in (("q", q), ("role", role), ("country", country)) if v}
        links = []
        if offset > 0:
            links.append(A(_("cj.admin.prev"), href="?" + urlencode({**base, "offset": max(0, offset - PAGE)}),
                           cls="btn btn-secondary btn-sm"))
        if offset + PAGE < total:
            links.append(A(_("cj.admin.next"), href="?" + urlencode({**base, "offset": offset + PAGE}),
                           cls="btn btn-secondary btn-sm"))
        pager = Div(*links, cls="cj-row")

    scope_text = _("cj.admin.scope_all") if scope.get("everywhere") else \
        _("cj.admin.scope_countries").format(c=", ".join(scope.get("countries") or scope.get("teams") or []) or "—")

    content = Div(
        Div(H1(_("cj.admin.title")), cls="cj-between"),
        admin_tabs("members", req, _),
        flash(_(f"cj.admin.msg_{msg}", _("cj.saved"))) if msg else "",
        flash(_(f"cj.error.{err}", err), "error") if err else "",
        Div(H2(_("cj.admin.tab_members")), Span(_("cj.admin.total").format(n=total), cls="cj-small"),
            cls="cj-between"),
        Span(scope_text, cls="cj-small"),
        _filters(q, role, country, roles, lang, _),
        Div(Div(_table(items, sel, query, roles_by_key, lang, _), pager, cls="wide"),
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


@rt("/community/admin/members/{pid}/roles")
async def post(req, pid: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    data = {"role_key": form.get("role_key") or "", "country": form.get("country") or None,
            "team": form.get("team") or None, "reason": (form.get("reason") or "").strip() or None}
    try:
        await community_api.assign_role(token, pid, data)
    except httpx.HTTPStatusError as e:
        return _back(pid, err=error_detail(e))
    except Exception:
        return _back(pid, err="save")
    return _back(pid, msg="role_added")


@rt("/community/admin/members/{pid}/roles/{hid}/remove")
async def post(req, pid: str, hid: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    reason = (form.get("reason") or "").strip()
    if not reason:
        return _back(pid, err="reason_required")
    try:
        await community_api.remove_role(token, hid, reason)
    except httpx.HTTPStatusError as e:
        return _back(pid, err=error_detail(e))
    except Exception:
        return _back(pid, err="save")
    return _back(pid, msg="role_removed")
