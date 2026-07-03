from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import auth.helper as auth_helper
import features.devices.api as devices_api

from components import page_shell, status_badge, fmt_date
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# DEVICE DETAIL
# ══════════════════════════════════════════════════════════════

@rt("/devices/{device_id}")
async def get(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    try:
        data = await devices_api.get_device(token, device_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse("/devices", status_code=302)
    except Exception:
        return RedirectResponse("/devices", status_code=302)

    d = data.get("device", {})
    cat = d.get("device_categories") or {}
    org = d.get("organizations") or {}
    logs = data.get("maintenance_logs", [])
    faults = data.get("fault_reports", [])
    docs = data.get("documents", [])

    qr_url = f"{req.base_url}d/{device_id}"

    # Maintenance log rows
    log_rows = [
        Tr(
            Td(fmt_date(l.get("performed_at", "")), style="font-size:0.875rem;"),
            Td(Span(l.get("type",""), cls="badge badge-blue")),
            Td(l.get("description","—"), style="font-size:0.875rem;"),
            Td((l.get("profiles") or {}).get("full_name","—"), style="font-size:0.875rem;"),
            Td(f"${l['cost_usd']}" if l.get("cost_usd") else "—", style="font-size:0.875rem;"),
        ) for l in logs
    ]

    # Fault rows
    fault_rows = [
        Tr(
            Td(fmt_date(f.get("reported_at","")), style="font-size:0.875rem;"),
            Td(f.get("reporter_name","—"), style="font-size:0.875rem;"),
            Td(f.get("description",""), style="font-size:0.875rem;"),
            Td(status_badge(f.get("severity","medium"), "severity")),
            Td(status_badge(f.get("status","open"), "fault")),
        ) for f in faults
    ]

    content = Div(
        A("← Devices", href="/devices",
        style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:14px;display:inline-block;"),
        Div(
            Div(
                Div(f"{cat.get('icon','🏥')} {cat.get('name','Device')}",
                    style="font-size:0.8rem;color:var(--c-text-3);margin-bottom:4px;"),
                H1(d.get("name",""), style="margin-bottom:4px;"),
                P(f"{d.get('manufacturer','')} {d.get('model','')} · {d.get('location','No location')}",
                style="color:var(--c-text-3);"),
            ),
            Div(status_badge(d.get("status","operational")),
                style="flex-shrink:0;"),
            cls="page-header", style="margin-bottom:14px;"
        ),
        # QR banner
        Div(
            Span("▣", style="font-size:1.3rem;"),
            Div(
                Div("Public QR page", style="font-size:0.75rem;font-weight:500;color:var(--c-primary);"),
                A(qr_url, href=qr_url, target="_blank",
                style="font-size:0.8rem;color:var(--c-primary-md);font-family:monospace;"),
            ),
            style="display:flex;align-items:center;gap:12px;background:var(--c-primary-lt);border:1px solid #a7d9ce;border-radius:var(--r-md);padding:12px 16px;margin-bottom:20px;"
        ),
        # Device info
        Div(
            Div(
                H3("Device information", style="margin-bottom:12px;"),
                Dl(
                    *[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;")
                    for k, v in [
                        ("Serial number", d.get("serial_number","—")),
                        ("Manufacturer",  d.get("manufacturer","—")),
                        ("Model",         d.get("model","—")),
                        ("Year",          str(d.get("manufacture_year","—"))),
                        ("Acquisition",   f"{d.get('acquisition_type','—')} · {fmt_date(d.get('acquisition_date',''))}"),
                        ("Location",      d.get("location","—")),
                        ("Organisation",  org.get("name","—")),
                    ]]
                ),
                cls="card"
            ),
            Div(
                H3("Maintenance", style="margin-bottom:12px;"),
                Dl(
                    *[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;")
                    for k, v in [
                        ("Last maintenance", fmt_date(d.get("last_maintenance",""))),
                        ("Next maintenance", fmt_date(d.get("next_maintenance",""))),
                    ]]
                ),
                cls="card"
            ),
            cls="two-col", style="margin-bottom:16px;"
        ),
        # Maintenance logs
        Div(
            H3("Maintenance history", style="margin-bottom:12px;"),
            Div(
                Table(
                    Thead(Tr(Th("Date"), Th("Type"), Th("Description"), Th("Technician"), Th("Cost"))),
                    Tbody(*log_rows) if log_rows else Tbody(
                        Tr(Td("No maintenance logged yet.", colspan="5",
                            style="color:var(--c-text-3);padding:20px;text-align:center;")))
                ),
                style="border:none;border-radius:0;"
            ),
            cls="card", style="margin-bottom:16px;"
        ),
        # Fault reports
        Div(
            H3("Fault reports", style="margin-bottom:12px;"),
            Div(
                Table(
                    Thead(Tr(Th("Date"), Th("Reported by"), Th("Description"), Th("Severity"), Th("Status"))),
                    Tbody(*fault_rows) if fault_rows else Tbody(
                        Tr(Td("No fault reports.", colspan="5",
                            style="color:var(--c-text-3);padding:20px;text-align:center;")))
                ),
                style="border:none;border-radius:0;"
            ),
            cls="card"
        ),
    )

    return page_shell(content, current="/devices", title=f"{d.get('name','Device')} — FixMyMedTech")

