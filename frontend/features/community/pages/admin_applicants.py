# /community/admin/applicants — new accounts still doing their welcome quests.
#
# Who sees what (permissions from utils/community.py):
#   view_applicants    see the list and an applicant's answers (in your country)
#   decide_applicants  assign a host, record the meeting, refuse or reopen
#   confirm_quests     mark Discord joined for someone who joined without linking

from urllib.parse import quote

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import (
    admin_tabs, first_admin_tab, perms, check_mark, flash, error_detail, fmt_dt,
)
from i18n import t as make_t

rt = APIRouter()

FILTERS = ("pending", "staff", "refused", "all")


def _status_badge(a: dict, _):
    if a["member_status"] == "refused":
        return Span(_("cj.admin.status_refused"), cls="badge badge-neutral")
    if a["member_status"] == "staff":
        return Span(_("cj.admin.status_staff"), cls="badge badge-ok")
    app = a.get("application") or {}
    if app.get("status") == "meeting_booked":
        return Span(_("cj.admin.status_meeting_booked"), cls="badge badge-warn")
    if app.get("status") == "met":
        return Span(_("cj.admin.status_met"), cls="badge badge-warn")
    return Span(_("cj.admin.status_new"), cls="badge badge-danger")


def _table(items, sel, status, _):
    if not items:
        return Div(P(_("cj.admin.no_applicants")), cls="cj-card")
    rows = []
    for a in items:
        app = a.get("application") or {}
        rows.append(Tr(
            Td(A(a.get("full_name") or a.get("username"), href=f"?status={status}&sel={a['id']}",
                 style="font-weight:500;")),
            Td(_(f"cj.kind.{app.get('kind') or 'other'}")),
            Td(", ".join(x for x in (a.get("city"), a.get("country")) if x)),
            Td(a.get("invited_by_name") or Span("—", cls="cj-small")),
            Td(f"{a['quests_done']} / {a['quests_total']}", cls="n"),
            Td(_status_badge(a, _)),
            Td(fmt_dt(a.get("created_at"))[:10]),
            cls="sel" if a["id"] == sel else None,
        ))
    return Div(Table(
        Thead(Tr(*[Th(_(k), scope="col", cls="n" if k == "cj.admin.col_quests" else None) for k in (
            "cj.admin.col_name", "cj.admin.col_kind", "cj.admin.col_place", "cj.admin.col_invited_by",
            "cj.admin.col_quests", "cj.admin.col_status", "cj.admin.col_joined")])),
        Tbody(*rows), cls="cj-table"), cls="cj-tablewrap")


def _detail(a, hosts, mine, _):
    app = a.get("application") or {}
    pid = a["id"]
    can_decide = "decide_applicants" in mine
    can_confirm = "confirm_quests" in mine
    quests = a.get("quests") or {}
    quest_rows = []
    for key in ("profile_complete", "intro_video", "meeting_held", "discord_joined", "consent_answered"):
        done = quests.get(key)
        extra = ""
        if key == "discord_joined" and not done and can_confirm:
            extra = Form(Button(_("cj.admin.mark_discord"), type="submit", cls="btn btn-secondary btn-sm"),
                         method="post", action=f"/community/admin/applicants/{pid}/quest/discord_joined")
        quest_rows.append(Div(check_mark(done), Div(Span(_(f"cj.quest.{key}"), cls="cj-quest-title"), extra,
                                                     cls="cj-quest-body"),
                              cls="cj-quest" + (" done" if done else "")))

    meeting_value = (app.get("meeting_at") or "")[:16]
    decide = ""
    if can_decide and a["member_status"] != "refused":
        decide = Div(
            Form(
                Div(Label(_("cj.admin.host"), cls="label", for_="host_id"),
                    Select(Option(_("cj.admin.no_host"), value=""),
                           *[Option(h["full_name"] + (f" ({h['country']})" if h.get("country") else ""),
                                    value=h["id"], selected=(h["id"] == app.get("host_id"))) for h in hosts],
                           name="host_id", id="host_id", cls="input"), cls="form-group"),
                Div(Label(_("cj.admin.meeting_at"), cls="label", for_="meeting_at"),
                    Input(type="datetime-local", id="meeting_at", name="meeting_at", value=meeting_value, cls="input"),
                    cls="form-group"),
                Div(Label(_("cj.admin.notes"), cls="label", for_="notes"),
                    Textarea(app.get("notes") or "", id="notes", name="notes", rows="2", cls="input"),
                    Span(_("cj.admin.notes_help"), cls="cj-small"), cls="form-group"),
                Button(_("cj.save"), type="submit", cls="btn btn-secondary btn-sm"),
                method="post", action=f"/community/admin/applicants/{pid}",
            ),
            Div(
                Form(Button(_("cj.admin.meeting_held"), type="submit", cls="btn btn-primary"),
                     method="post", action=f"/community/admin/applicants/{pid}/meeting-held")
                if not quests.get("meeting_held") else Span(_("cj.admin.meeting_recorded"), cls="badge badge-ok"),
                cls="cj-row",
            ),
            Span(_("cj.admin.meeting_held_help"), cls="cj-small"),
            Details(
                Summary(_("cj.admin.refuse"), style="cursor:pointer;color:var(--danger);font-weight:500;"),
                Form(
                    Label(_("cj.admin.refuse_reason"), cls="label", for_="reason"),
                    Textarea(id="reason", name="reason", rows="2", cls="input", required=True),
                    Span(_("cj.admin.refuse_help"), cls="cj-small"),
                    Button(_("cj.admin.refuse_confirm"), type="submit", cls="btn btn-danger btn-sm",
                           style="margin-top:8px;"),
                    method="post", action=f"/community/admin/applicants/{pid}/refuse",
                ),
            ),
            style="display:flex;flex-direction:column;gap:12px;",
        )
    elif can_decide:
        decide = Div(
            P(_("cj.admin.refused_reason").format(reason=app.get("decision_reason") or "—")),
            Form(Button(_("cj.admin.reopen"), type="submit", cls="btn btn-secondary btn-sm"),
                 method="post", action=f"/community/admin/applicants/{pid}/reopen"),
        )

    return Div(
        H2(a.get("full_name") or a.get("username")),
        Span(" · ".join(x for x in (_(f"cj.kind.{app.get('kind') or 'other'}"), app.get("organisation"),
                                    a.get("country_trained") and _("cj.admin.trained_in").format(c=a["country_trained"]))
                        if x), cls="cj-small"),
        P(f"“{app['motivation']}”", style="color:var(--text);") if app.get("motivation") else "",
        Dl(
            Dt(_("cj.admin.email")), Dd(A(a["email"], href=f"mailto:{a['email']}") if a.get("email") else "—"),
            Dt(_("cj.admin.col_place")), Dd(", ".join(x for x in (a.get("city"), a.get("country")) if x) or "—"),
            Dt(_("cj.admin.heard_from")), Dd(app.get("heard_from") or "—"),
            Dt(_("cj.admin.why_bme")), Dd(a.get("why_bme") or "—"),
            Dt(_("cj.admin.join_path")), Dd(_(f"cj.join_path.{a.get('join_path') or 'community'}")),
            cls="cj-dl",
        ),
        Div(*quest_rows),
        decide,
        cls="cj-card", aria_label=a.get("full_name") or "",
    )


@rt("/community/admin")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    target = first_admin_tab(req)
    if not target:
        return RedirectResponse("/community", status_code=302)
    return RedirectResponse(target, status_code=302)


@rt("/community/admin/applicants")
async def get(req, status: str = "pending", sel: str = "", msg: str = "", err: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    mine = perms(req)
    status = status if status in FILTERS else "pending"
    try:
        data = await community_api.list_applicants(token, status=status)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return RedirectResponse("/community", status_code=302)
        data = {"items": [], "counts": {}, "scope": {}}
    items = data.get("items") or []
    counts = data.get("counts") or {}
    scope = data.get("scope") or {}

    detail = ""
    if sel:
        selected = next((a for a in items if a["id"] == sel), None)
        if selected is None:
            try:
                selected = await community_api.get_applicant(token, sel)
            except Exception:
                selected = None
        if selected:
            hosts = []
            if "decide_applicants" in mine:
                try:
                    hosts = await community_api.list_hosts(token)
                except Exception:
                    hosts = []
            detail = _detail(selected, hosts, mine, _)

    count_for = {"pending": counts.get("applicant", 0), "staff": counts.get("staff", 0),
                 "refused": counts.get("refused", 0),
                 "all": sum(v for k, v in counts.items() if k != "member")}
    filters = Div(*[A(f"{_(f'cj.admin.filter_{f}')} · {count_for[f]}", href=f"?status={f}",
                      cls="cj-tab" + (" on" if f == status else "")) for f in FILTERS], cls="cj-row")
    scope_text = _("cj.admin.scope_all") if scope.get("everywhere") else \
        _("cj.admin.scope_countries").format(c=", ".join(scope.get("countries") or []) or "—")

    content = Div(
        Div(H1(_("cj.admin.title")), cls="cj-between"),
        admin_tabs("applicants", req, _),
        flash(_(f"cj.admin.msg_{msg}", _("cj.saved"))) if msg else "",
        flash(_(f"cj.error.{err}", err), "error") if err else "",
        Div(H2(_("cj.admin.tab_applicants")), filters, cls="cj-between"),
        Span(scope_text, cls="cj-small"),
        Div(Div(_table(items, sel, status, _), cls="wide"), Div(detail, cls="side") if detail else "",
            cls="cj-split"),
        cls="cj",
    )
    return page_shell(content, current="/community/admin", title=_("cj.title.admin"), lang=lang)


def _back(pid, msg="", err=""):
    q = f"sel={pid}&status=all"
    if msg:
        q += f"&msg={msg}"
    if err:
        q += f"&err={quote(err)}"
    return RedirectResponse(f"/community/admin/applicants?{q}", status_code=303)


async def _do(req, pid, call, msg):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await call(token)
    except httpx.HTTPStatusError as e:
        return _back(pid, err=error_detail(e))
    except Exception as e:
        return _back(pid, err=str(e))
    return _back(pid, msg=msg)


@rt("/community/admin/applicants/{pid}")
async def post(req, pid: str):
    form = await req.form()
    data = {"host_id": form.get("host_id") or "", "notes": form.get("notes") or ""}
    meeting = (form.get("meeting_at") or "").strip()
    if meeting:
        data["meeting_at"] = meeting
    else:
        data["clear_meeting"] = True
    return await _do(req, pid, lambda t: community_api.update_applicant(t, pid, data), "saved")


@rt("/community/admin/applicants/{pid}/meeting-held")
async def post(req, pid: str):
    return await _do(req, pid, lambda t: community_api.meeting_held(t, pid), "meeting")


@rt("/community/admin/applicants/{pid}/quest/{quest_key}")
async def post(req, pid: str, quest_key: str):
    return await _do(req, pid, lambda t: community_api.confirm_quest(t, pid, quest_key), "quest")


@rt("/community/admin/applicants/{pid}/refuse")
async def post(req, pid: str):
    form = await req.form()
    reason = (form.get("reason") or "").strip()
    return await _do(req, pid, lambda t: community_api.refuse_applicant(t, pid, reason), "refused")


@rt("/community/admin/applicants/{pid}/reopen")
async def post(req, pid: str):
    return await _do(req, pid, lambda t: community_api.reopen_applicant(t, pid), "reopened")
