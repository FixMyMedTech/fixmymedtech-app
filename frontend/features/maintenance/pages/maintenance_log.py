from fasthtml.common import *
from starlette.responses import RedirectResponse

# __ API imports __
import features.auth.helper as auth_helper
import features.faults.api as faults_api
import features.maintenance.api as maintenance_api
import features.auth.api as auth_api

from components import *
from components import page_shell
from i18n import t as make_t
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# START MAINTENANCE LOG
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/maintenance-log")
async def get(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/maintenance-log", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
        full_name = me.get("full_name") or req.session.get("user_email", "")
    except Exception:
        full_name = req.session.get("user_email", "")

    assignees = []
    try:
        assignees = await faults_api.get_fault_assignees(token, device_id)
    except Exception:
        assignees = []

    assignee_options = [Option(_("maintenance_log.assignee_none"), value="")]
    for a in assignees:
        role_label = _("role." + (a.get("role") or "technician"))
        assignee_options.append(
            Option(f"{a.get('full_name','')} — {role_label}", value=a["id"])
        )

    content = Div(
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}",
              style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:block;margin-bottom:16px;"),
            H2(_("maintenance_log.heading"), style="margin-bottom:6px;"),
            P(_("maintenance_log.desc"),
              style="margin-bottom:16px;"),
            Div(
                Label(_("maintenance_log.type_label"), cls="label"),
                Div(
                    *[Label(Input(type="radio", name="type", value=v,
                                  checked=(v=="preventive")),
                             f" {_(f'maintenance_log.type_{v}')}",
                             style="display:block;padding:8px 10px;margin-bottom:6px;font-size:0.875rem;cursor:pointer;")
                      for v in ["preventive", "corrective", "inspection"]],
                )
            ),
            Div(
                Label(_("maintenance_log.description_label"), cls="label"),
                Textarea(name="description", cls="input", rows="4",
                         placeholder=_("maintenance_log.description_placeholder")),
                cls="form-group", style="margin-top:12px;"
            ),
            Div(
                Label(_("maintenance_log.assignee_label"), cls="label"),
                Select(
                    *assignee_options,
                    name="assigned_to",
                    cls="input",
                ),
                cls="form-group",
                style="margin-top:12px;"
            ),
            Div(
                Label(_("report_fault.name_label"), cls="label"),
                Div(full_name, cls="input",
                    style="opacity:.7;"),
                cls="form-group", style="margin-top:12px;"
            ),
            Button(_("maintenance_log.submit"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:8px;"),
            style="padding:16px;"
        ),
        cls="card", style="max-width:560px;margin:24px auto;"
    )

    return page_shell(
        Form(content, method="post", action=f"/d/{device_id}/maintenance-log"),
        current="/devices", title=_("title.maintenance_log"), lang=lang
    )


@rt("/d/{device_id}/maintenance-log")
async def post(req, device_id: str, description: str = "",
               type: str = "preventive", assigned_to: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/maintenance-log", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    data = {
        "device_id": device_id,
        "type": type if type in ("preventive", "corrective", "inspection") else "preventive",
        "description": description or None,
    }
    if assigned_to:
        data["assigned_to"] = assigned_to

    try:
        await maintenance_api.create_maintenance_log(token, data)
    except Exception:
        pass

    return page_shell(
        Div(
            Div(
                Div("✓", style="width:52px;height:52px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.3rem;display:flex;align-items:center;justify-content:center;margin:0 auto 14px;"),
                H2(_("maintenance_log.success_heading")),
                P(_("maintenance_log.success_msg")),
                A(_("maintenance_log.success_back"), href=f"/d/{device_id}",
                  cls="btn btn-secondary", style="margin-top:16px;"),
                style="text-align:center;padding:40px 24px;"
            ),
            cls="card", style="max-width:560px;margin:80px auto;"
        ),
        current="/devices", lang=lang
    )