from ast import Div

from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api

from components import *

from components import page_shell, status_badge, fmt_date, pub_shell
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# PUBLIC QR PAGE
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}")
async def get(req, device_id: str):
    try:
        data = await devices_api.get_device_public(device_id)
    except Exception:
        return pub_shell(
            Div(
                Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                H2("Device not found"),
                P("This QR code doesn't match any registered device."),
                A("Register new device", href=f"/device/{device_id}/new", cls="btn btn-primary",
                style="margin-top:20px;"),
                style="text-align:center;padding:60px 24px;"
            )
        )

    d = data.get("device", {})
    docs = data.get("documents", [])
    faults = data.get("recent_faults", [])
    cat = d.get("device_categories") or {}

    nm = d.get("next_maintenance","")
    import datetime
    overdue = nm and nm < datetime.datetime.now().isoformat()

    doc_items = [
        A(
            Span("▶" if doc.get("type")=="video" else "📄" if doc.get("type")=="manual" else "📋",
                 style="font-size:1.2rem;"),
            Div(
                Div(doc.get("title",""), style="font-weight:500;font-size:0.875rem;"),
                Div(f"{doc.get('type','')} · {doc.get('language','').upper()}",
                    style="font-size:0.75rem;color:var(--c-text-3);"),
            ),
            href=doc.get("url","#"), target="_blank",
            style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-md);text-decoration:none;color:var(--c-text);margin-bottom:8px;"
        ) for doc in docs
    ]

    fault_items = [
        Div(
            Div(
                status_badge(f.get("severity","medium"), "severity"),
                status_badge(f.get("status","open"), "fault"),
                Span(fmt_date(f.get("reported_at","")),
                     style="font-size:0.72rem;color:var(--c-text-3);"),
                style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;"
            ),
            P(f.get("description",""), style="font-size:0.875rem;margin:0;"),
            style="background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-md);padding:12px;margin-bottom:8px;"
        ) for f in faults
    ]

    content = Div(
        # Header
        Div(
            Div(Span("✚", cls="pub-cross"), " FixMyMedTech", cls="pub-logo"),
            cls="pub-header"
        ),
        # Device identity
        Div(
            Div(cat.get("icon","🏥"), cls="dev-icon"),
            Div(
                Div(cat.get("name","Device"), cls="dev-cat"),
                Div(d.get("name",""), cls="dev-name"),
                Div(f"{d.get('manufacturer','')} · SN: {d.get('serial_number','')}".strip(" ·"),
                    cls="dev-meta"),
            ),
            Div(
                status_badge(d.get("status","operational")),
                Div(d.get("location",""), cls="dev-loc"),
                cls="dev-status"
            ),
            cls="device-identity"
        ),
        # Maintenance warning
        Div(
            Span("⚠", style="font-size:1rem;flex-shrink:0;"),
            Div(
                Strong("Maintenance overdue"),
                P(f"Due {fmt_date(nm)}. Contact your biomedical engineer."),
            ),
            cls="warn-bar"
        ) if overdue else "",
        # Manuals
        Div(
            Div(
                Strong("Do you want more information?", style="font-size:0.875rem;"),
                P("Check the user and maintenance quick guidelines.", style="font-size:0.8rem;margin:2px 0 0;"),
            ),
            A(Span("ⓘ", style="font-size:1.3rem;"),
              Div("User guide"),
              href=f"/d/{device_id}/report",
              cls="btn btn-secondary btn-sm",
              style = "margin-left:6px;justify-content:center"),
            A(Span("🔧", style="font-size:1.3rem;"),
              Div("Maintenance guide"),
              href=f"/d/{device_id}/report",
              cls="btn btn-secondary btn-sm",
              style = "margin-left:6px;justify-content:center"),
            cls="report-cta"
        ),
        # Report fault CTA
        Div(
            Div(
                Strong("Found a problem?", style="font-size:0.875rem;"),
                P("Report it to the biomed team.", style="font-size:0.8rem;margin:2px 0 0;"),
            ),
            A("⚠ Report fault", href=f"/d/{device_id}/report",
              cls="btn btn-danger btn-sm"),
            cls="report-cta"
        ),
        # Device info
        Div(
            H3("Device information",
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            Dl(
                *[Div(Dt(k), Dd(v), cls="info-row")
                  for k, v in [
                      ("Status",       d.get("status","—")),
                      ("Location",     d.get("location","—")),
                      ("Manufacturer", d.get("manufacturer","—")),
                      ("Model",        d.get("model","—")),
                      ("Serial no.",   d.get("serial_number","—")),
                      ("Last maint.",  fmt_date(d.get("last_maintenance",""))),
                      ("Next maint.",  fmt_date(nm)),
                  ]],
                cls="info-list"
            ),
            cls="pub-section"
        ),
        # Manuals
        Div(
            H3("Manuals & documents",
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            *doc_items if doc_items else [P("No documents attached.", style="color:var(--c-text-3);font-size:0.875rem;")],
            cls="pub-section"
        ) if docs else "",
        # Recent faults
        Div(
            H3("Recent fault reports",
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            *fault_items if fault_items else [P("No fault reports on record.", style="color:var(--c-text-3);font-size:0.875rem;")],
            cls="pub-section"
        ),
        # Footer
        Div("FixMyMedTech · Powered by CareAgain", cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{d.get('name','Device')} — FixMyMedTech")
