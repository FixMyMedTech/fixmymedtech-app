from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.devices.api as devices_api

from components import page_shell, status_badge, fmt_date
from i18n import t as make_t
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# MAINTENANCE LOG DETAIL
# ══════════════════════════════════════════════════════════════

@rt("/device/{device_id}/log/{log_id}")
async def get(req, device_id: str, log_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        log = await devices_api.get_maintenance_log(token, log_id)
    except Exception:
        return RedirectResponse(f"/device/{device_id}", status_code=302)

    device = log.get("device") or {}
    performed_by = log.get("performed_by_profile") or {}
    assigned = log.get("assigned_to_profile") or {}

    rows = [
        (_("log_detail.type"),         _(f"maintenance_log.type_{log.get('type', 'preventive')}")),
        (_("log_detail.performed_at"), fmt_date(log.get("performed_at", ""))),
        (_("log_detail.technician"),   performed_by.get("full_name", _("common.fallback"))),
        (_("log_detail.assigned_to"),  assigned.get("full_name", _("common.fallback"))),
        (_("log_detail.parts_replaced"), log.get("parts_replaced", _("common.fallback"))),
        (_("log_detail.cost"),         f"${log['cost_usd']}" if log.get("cost_usd") else _("common.fallback")),
        (_("log_detail.next_due"),     fmt_date(log.get("next_due", ""))),
    ]

    content = Div(
        A(_("device_detail.back"), href=f"/device/{device_id}",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:14px;display:inline-block;"),
        Div(
            Div(
                Div(f"{device.get('name','')}",
                    style="font-size:0.8rem;color:var(--c-text-3);margin-bottom:4px;"),
                H1(_("log_detail.heading"), style="margin-bottom:4px;"),
                P(_("log_detail.desc"), style="color:var(--c-text-3);"),
            ),
            cls="page-header", style="margin-bottom:14px;"
        ),
        Div(
            Div(
                H3(_("log_detail.info"), style="margin-bottom:12px;"),
                Dl(
                    *[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                          style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;gap:16px;")
                      for k, v in rows],
                ),
                cls="card", style="margin-bottom:16px;"
            ),
            Div(
                H3(_("log_detail.description"), style="margin-bottom:12px;"),
                P(log.get("description", _("log_detail.no_description")),
                  style="font-size:0.9rem;white-space:pre-wrap;color:var(--c-text-2);"),
                cls="card",
            ),
        ),
    )

    return page_shell(content, current="/devices", lang=lang, title=f"{_('title.device_detail')}")
