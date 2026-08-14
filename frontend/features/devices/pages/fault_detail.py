from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.faults.api as faults_api

from components import page_shell, status_badge, fmt_date
from i18n import t as make_t
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# FAULT REPORT DETAIL
# ══════════════════════════════════════════════════════════════

@rt("/device/{device_id}/fault/{fault_id}")
async def get(req, device_id: str, fault_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        fault = await faults_api.get_fault(token, fault_id)
    except Exception:
        return RedirectResponse(f"/device/{device_id}", status_code=302)

    device = fault.get("device") or {}
    assigned = fault.get("assigned_to_profile") or {}
    reported_by = fault.get("reported_by_profile") or {}

    rows = [
        (_("fault_detail.status"),      status_badge(fault.get("status", "open"), "fault", lang=lang)),
        (_("fault_detail.severity"),    status_badge(fault.get("severity", "medium"), "severity", lang=lang)),
        (_("fault_detail.reported_at"), fmt_date(fault.get("reported_at", ""))),
        (_("fault_detail.reported_by"), reported_by.get("full_name") or fault.get("reporter_name", _("common.fallback"))),
        (_("fault_detail.assigned_to"), assigned.get("full_name", _("common.fallback"))),
        (_("fault_detail.resolved_at"), fmt_date(fault.get("resolved_at", ""))),
    ]

    content = Div(
        A(_("device_detail.back"), href=f"/device/{device_id}",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:14px;display:inline-block;"),
        Div(
            Div(
                Div(f"{device.get('name','')}",
                    style="font-size:0.8rem;color:var(--c-text-3);margin-bottom:4px;"),
                H1(_("fault_detail.heading"), style="margin-bottom:4px;"),
                P(_("fault_detail.desc"), style="color:var(--c-text-3);"),
            ),
            cls="page-header", style="margin-bottom:14px;"
        ),
        Div(
            Div(
                H3(_("fault_detail.info"), style="margin-bottom:12px;"),
                Dl(
                    *[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                          style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;gap:16px;")
                      for k, v in rows],
                ),
                cls="card", style="margin-bottom:16px;"
            ),
            Div(
                H3(_("fault_detail.description"), style="margin-bottom:12px;"),
                P(fault.get("description", ""),
                  style="font-size:0.9rem;white-space:pre-wrap;"),
                cls="card", style="margin-bottom:16px;"
            ),
            Div(
                H3(_("fault_detail.resolution"), style="margin-bottom:12px;"),
                P(fault.get("resolution_notes", _("fault_detail.no_resolution")),
                  style="font-size:0.9rem;white-space:pre-wrap;color:var(--c-text-2);"),
                cls="card",
            ) if fault.get("resolution_notes") else "",
        ),
    )

    return page_shell(content, current="/devices", lang=lang, title=f"{_('title.device_detail')}")
