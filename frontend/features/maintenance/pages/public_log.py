from fasthtml.common import *
from starlette.responses import RedirectResponse

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.faults.api as faults_api
import features.maintenance.api as maintenance_api

from components import *
from components import page_shell, status_badge, fmt_date, pub_shell, assignee_options
from i18n import t as make_t

rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# PUBLIC MAINTENANCE LOG DETAIL
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/log/{log_id}", methods=["get"])
async def get_log_public(req, device_id: str, log_id: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        log = await maintenance_api.get_maintenance_log_public(log_id)
    except Exception:
        return pub_shell(
            Div(
                Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                H2(_("public_qr.not_found")),
                P(_("public_qr.not_found_msg")),
                A(_("public_qr.back"), href=f"/d/{device_id}", cls="btn btn-primary",
                  style="margin-top:20px;"),
                style="text-align:center;padding:60px 24px;"
            ),
            lang=lang
        )

    device = log.get("device") or {}
    performed_by = log.get("performed_by_profile") or {}
    assigned = log.get("assigned_to_profile") or {}

    sec_head = lambda t: H3(t,
        style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;")

    rows = [
        (_("log_detail.status"),       status_badge(log.get("status", "open"), "log", lang=lang)),
        (_("log_detail.type"),         _(f"maintenance_log.type_{log.get('type', 'preventive')}")),
        (_("log_detail.performed_at"), fmt_date(log.get("performed_at", ""))),
        (_("log_detail.technician"),   performed_by.get("full_name", _("common.fallback"))),
        (_("log_detail.assigned_to"),  assigned.get("full_name", _("common.fallback"))),
        (_("log_detail.parts_replaced"), log.get("parts_replaced", _("common.fallback"))),
        (_("log_detail.cost"),         f"${log['cost_usd']}" if log.get("cost_usd") else _("common.fallback")),
        (_("log_detail.next_due"),     fmt_date(log.get("next_due", ""))),
    ]

    # Botón editar solo si hay sesión con rol técnico/admin
    edit_btn = ""
    token = auth_helper.get_token(req)
    if token:
        try:
            me = await auth_api.get_me(token)
        except Exception:
            me = {}
        if auth_helper.user_can_edit(me, device.get("organization_id")):
            edit_btn = Div(
                A(_("log_detail.edit"), href=f"/d/{device_id}/log/{log['id']}/edit",
                  cls="btn btn-primary", style="width:100%;justify-content:center;"),
                cls="pub-section"
            )

    content = Div(
        # Title
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}",
              style="font-size:0.8rem;color:var(--c-text-3);text-decoration:none;margin-bottom:10px;display:inline-block;"),
            Div(f"{device.get('name','')}",
                style="font-size:0.78rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;"),
            H1(_("log_detail.heading"), style="font-family:var(--font-display);font-size:1.25rem;margin:2px 0 0;"),
            cls="pub-section"
        ),
        # Details
        Div(
            sec_head(_("log_detail.info")),
            Dl(
                *[Div(Dt(k), Dd(v), cls="info-row") for k, v in rows],
                cls="info-list", style="padding:0;"
            ),
            cls="pub-section"
        ),
        # Description
        Div(
            sec_head(_("log_detail.description")),
            P(log.get("description", _("log_detail.no_description")),
              style="font-size:0.9rem;white-space:pre-wrap;color:var(--c-text-2);"),
            cls="pub-section"
        ),
        edit_btn,
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{_('log_detail.heading')} — {_('brand')}", lang=lang)


# ══════════════════════════════════════════════════════════════
# PUBLIC MAINTENANCE LOG EDIT
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/log/{log_id}/edit", methods=["get"])
async def get_log_edit(req, device_id: str, log_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/log/{log_id}/edit", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}
    log_obj = await maintenance_api.get_maintenance_log_public(log_id)
    log_device = (log_obj.get("device") or {}) if isinstance(log_obj, dict) else {}
    if not auth_helper.user_can_edit(me, log_device.get("organization_id")):
        return RedirectResponse(f"/d/{device_id}/log/{log_id}", status_code=302)

    try:
        log = await maintenance_api.get_maintenance_log_public(log_id)
    except Exception:
        return RedirectResponse(f"/d/{device_id}", status_code=302)

    device = log.get("device") or {}
    assignees = []
    try:
        assignees = await faults_api.get_fault_assignees(token, device_id)
    except Exception:
        assignees = []

    content = Div(
        # Title
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}/log/{log_id}",
              style="font-size:0.8rem;color:var(--c-text-3);text-decoration:none;margin-bottom:10px;display:inline-block;"),
            Div(f"{device.get('name','')}",
                style="font-size:0.78rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;"),
            H1(_("log_detail.edit"), style="font-family:var(--font-display);font-size:1.25rem;margin:2px 0 0;"),
            cls="pub-section"
        ),
        _log_edit_form(log, device_id, assignees, lang),
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{_('log_detail.edit')} — {_('brand')}", lang=lang)


@rt("/d/{device_id}/log/{log_id}/edit", methods=["post"])
async def post_log_edit(req, device_id: str, log_id: str, type: str = "",
                        status: str = "", assigned_to: str = "", description: str = "",
                        parts_replaced: str = "", cost_usd: str = "",
                        next_due: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/log/{log_id}/edit", status_code=302)

    data = {}
    if type:
        data["type"] = type
    if status:
        data["status"] = status
    if assigned_to:
        data["assigned_to"] = assigned_to
    if description is not None:
        data["description"] = description
    if parts_replaced is not None:
        data["parts_replaced"] = parts_replaced
    if cost_usd:
        data["cost_usd"] = cost_usd
    if next_due:
        data["next_due"] = next_due
    try:
        await maintenance_api.update_maintenance_log(token, log_id, data)
    except Exception:
        pass

    return RedirectResponse(f"/d/{device_id}/log/{log_id}", status_code=303)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _log_edit_form(log, device_id, assignees, lang):
    _ = make_t(lang)
    sec_head = lambda t: H3(t,
        style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;")
    return Form(
        Div(
            sec_head(_("log_detail.edit")),
            Div(
                Label(_("log_detail.status"), cls="label"),
                Select(*[Option(_(f"badge.{v}"), value=v,
                                selected=(log.get("status", "open") == v))
                         for v in ["open", "in_progress", "closed"]],
                       name="status", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.type"), cls="label"),
                Select(*[Option(_(f"maintenance_log.type_{v}"), value=v,
                                selected=(log.get("type") == v))
                         for v in ["preventive", "corrective", "inspection"]],
                       name="type", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.assigned_to"), cls="label"),
                Select(*assignee_options(assignees, log.get("assigned_to") or "", lang),
                       name="assigned_to", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.description"), cls="label"),
                Textarea(log.get("description", ""), name="description", rows="3",
                         cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.parts_replaced"), cls="label"),
                Input(type="text", name="parts_replaced", value=log.get("parts_replaced", ""),
                      cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.cost"), cls="label"),
                Input(type="number", step="0.01", name="cost_usd",
                      value=log.get("cost_usd", ""), cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.next_due"), cls="label"),
                Input(type="date", name="next_due",
                      value=str(log.get("next_due", ""))[:10], cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Button(_("common.save"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:14px;"),
        ),
        method="post", action=f"/d/{device_id}/log/{log['id']}/edit",
    )