from fasthtml.common import *
import features.tasks.api as tasks_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell, status_badge, fmt_date

rt = APIRouter()


@rt("/tasks")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        tasks = await tasks_api.get_my_tasks(token)
    except Exception:
        tasks = []

    task_rows = []
    for t_item in tasks:
        is_fault = t_item.get("type") == "fault"
        type_label = _("tasks.type_fault") if is_fault else _("tasks.type_maintenance")
        href = f"/faults/{t_item['id']}" if is_fault else f"/maintenance-logs/{t_item['id']}"
        task_rows.append(
            Tr(
                Td(A(t_item.get("title", ""), href=href,
                      style="color:var(--c-primary);text-decoration:none;font-weight:500;")),
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
                Th("Device"),
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
        table = Div(
            Div("📋", style="width:56px;height:56px;background:var(--c-blue-lt);color:var(--c-primary);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
            P(_("tasks.empty"), style="color:var(--c-text-3);font-size:0.9rem;text-align:center;"),
            style="text-align:center;padding:60px 24px;"
        )

    content = Div(
        Div(H1(_("tasks.heading")), cls="page-header"),
        Div(table, style="max-width:960px;"),
    )
    return page_shell(content, current="/tasks", title=_("title.tasks"), lang=lang)
