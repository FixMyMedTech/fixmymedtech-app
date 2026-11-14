# features/tasks/pages.py — "My work": the repairs and services assigned to
# me, plus (wave 3) the engineer's open requests nearby and the community
# tasks I took, so one page answers "what should I do next?".

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.tasks.api as tasks_api
import features.calls.api as calls_api
import features.community.api as community_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell, status_badge, fmt_date, page_head

rt = APIRouter()

TASKS_CSS = """
.mywork{max-width:960px;}
.mywork .muted{color:var(--text-muted);font-size:14px;}
.mw-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-bottom:16px;}
.mw-row{display:flex;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--border);border-left:4px solid var(--warn);border-radius:var(--radius-control);margin-bottom:8px;background:var(--surface);text-decoration:none;color:var(--text);}
.mw-row:hover{border-color:var(--primary);}
.mw-row.is-danger{border-left-color:var(--danger);} .mw-row.is-primary{border-left-color:var(--primary);}
.mw-row .grow{flex:1;min-width:0;}
.mw-row b{display:block;font-size:14px;}
.mw-row small{font-size:12px;color:var(--text-muted);}
.mw-count{font-size:12px;font-weight:600;color:var(--text-muted);background:var(--sunken);border-radius:var(--radius-pill);padding:1px 8px;margin-left:6px;}
.mw-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;}
"""


@rt("/tasks")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        tasks = await tasks_api.get_my_tasks(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        tasks = []
    except Exception:
        tasks = []

    is_member = req.session.get("member_status", "member") == "member"
    inbox, board = {}, {}
    if is_member:
        try:
            inbox = await calls_api.inbox(token)
        except Exception:
            inbox = {}
        try:
            board = await community_api.task_board(token)
        except Exception:
            board = {}

    task_rows = []
    for t_item in tasks:
        is_fault = t_item.get("type") == "fault"
        type_label = _("tasks.type_fault") if is_fault else _("tasks.type_maintenance")
        href = (f"/d/{t_item['device_id']}/fault/{t_item['id']}"
                if is_fault else f"/d/{t_item['device_id']}/log/{t_item['id']}")
        task_rows.append(
            Tr(
                Td(A(t_item.get("title", ""), href=href,
                      style="color:var(--primary);text-decoration:none;font-weight:500;")),
                Td(type_label),
                Td(status_badge(t_item.get("severity", ""), "severity") if is_fault
                   else status_badge(t_item.get("severity", ""), "fault")),
                Td(status_badge(t_item.get("status", ""), "fault")),
                Td(fmt_date(t_item.get("date", ""))),
            )
        )

    if task_rows:
        table = Table(
            Thead(Tr(
                Th(_("common.device")),
                Th(_("tasks.type")),
                Th(_("tasks.severity")),
                Th(_("tasks.status")),
                Th(_("tasks.date")),
            )),
            Tbody(*task_rows),
            cls="table",
            style="width:100%;"
        )
    else:
        table = P(_("tasks.empty"), cls="muted", style="text-align:center;padding:24px;")

    # Wave 3: requests near me (call an engineer) and my community tasks.
    side = []
    near = inbox.get("open") or []
    offers = inbox.get("mine") or []
    if inbox and (inbox.get("can_offer") or near or offers):
        rows = [A(Div(B(r.get("device_name", "")),
                      Small(" · ".join(x for x in (r.get("location") or "",
                                                    _(f"call.urgency_{r.get('urgency')}") if r.get("urgency") else "") if x)),
                      cls="grow"),
                  Span(_("call.tier_" + (r.get("tier") or "city")), cls="badge badge-neutral"),
                  href=f"/requests/{r['fault_id']}",
                  cls=f"mw-row is-{'danger' if r.get('urgency') == 'now' else 'warn'}") for r in near[:4]]
        side.append(Div(
            Div(H3(_("call.near_you"), Span(str(len(near)), cls="mw-count"), cls="card-title"),
                A(_("wave3.see_all"), href="/requests", cls="btn btn-secondary btn-sm"), cls="mw-head"),
            *(rows or [P(_("call.nothing_new"), cls="muted")]),
            P(_("wave3.offers_waiting").format(n=len(offers)), cls="muted") if offers else "",
            cls="card",
        ))
    mine = board.get("mine") or []
    if board:
        rows = [A(Div(B(tk.get("title", "")), Small(_(f"w5.kind.{tk.get('kind')}")), cls="grow"),
                  Span(f"+{tk.get('points', 0)}", style="font-weight:700;color:var(--primary);"),
                  href="/community/tasks#mine", cls="mw-row is-primary") for tk in mine[:4]]
        side.append(Div(
            Div(H3(_("wave3.my_community_tasks"), Span(str(len(mine)), cls="mw-count"), cls="card-title"),
                A(_("w5.board_title"), href="/community/tasks", cls="btn btn-secondary btn-sm"), cls="mw-head"),
            *(rows or [P(_("wave3.no_community_tasks").format(n=len(board.get("open") or [])), cls="muted")]),
            cls="card",
        ))

    content = Div(
        Style(TASKS_CSS),
        page_head(_("tasks.heading"), "", "tasks", ""),
        Div(*side, cls="mw-grid") if side else "",
        Div(H3(_("wave3.assigned_to_me"), cls="card-title"), table, cls="card"),
        cls="mywork",
    )
    return page_shell(content, current="/tasks", title=_("title.tasks"), lang=lang)
