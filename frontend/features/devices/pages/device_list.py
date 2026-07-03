from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import auth.helper as auth_helper
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api

from components import page_shell, status_badge, fmt_date
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# DEVICES LIST
# ══════════════════════════════════════════════════════════════

@rt("/devices")
async def get(req, status: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    try:
        devices = await devices_api.get_devices(token, status or None)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        devices = []
    except Exception:
        devices = []

    status_filters = [
        ("", "All"), ("operational", "Operational"),
        ("maintenance", "Maintenance"), ("fault", "Fault"),
        ("decommissioned", "Decommissioned"),
    ]

    pills = [
        A(label, href=f"/devices?status={val}",
        cls=f"pill {'active' if status == val else ''}")
        for val, label in status_filters
    ]

    rows = []
    for d in devices:
        cat = d.get("device_categories") or {}
        nm = d.get("next_maintenance", "")
        overdue = nm and nm < __import__("datetime").datetime.now().isoformat()
        rows.append(Tr(
            Td(Div(d.get("name", ""), style="font-weight:500;font-size:0.875rem;color:var(--c-text);"),
            Div(f"{d.get('manufacturer','')} {d.get('model','')}".strip(),
                style="font-size:0.75rem;color:var(--c-text-3);")),
            Td(f"{cat.get('icon','🏥')} {cat.get('name','—')}", style="font-size:0.875rem;"),
            Td(d.get("location", "—"), style="font-size:0.875rem;"),
            Td(status_badge(d.get("status", "operational"))),
            Td(
                Span(fmt_date(nm), cls="overdue" if overdue else ""),
                Span("overdue", cls="overdue-tag") if overdue else ""
            ),
            Td(A("View", href=f"/devices/{d['id']}", cls="btn btn-secondary btn-sm")),
        ))

    table = Div(
        Table(
            Thead(Tr(Th("Device"), Th("Category"), Th("Location"),
                    Th("Status"), Th("Next maint."), Th(""))),
            Tbody(*rows) if rows else Tbody(
                Tr(Td("No devices found.", colspan="6",
                    style="text-align:center;padding:32px;color:var(--c-text-3);"))
            )
        ),
        cls="table-wrap"
    )

    content = Div(
        Div(
            Div(H1("Devices"), P(f"{len(devices)} device{'s' if len(devices)!=1 else ''} registered",
                                style="color:var(--c-text-3);")),
            A("+ Add device", href="/devices/new", cls="btn btn-primary"),
            cls="page-header"
        ),
        Div(*pills, cls="toolbar"),
        table,
    )

    return page_shell(content, current="/devices", title="Devices — FixMyMedTech")
