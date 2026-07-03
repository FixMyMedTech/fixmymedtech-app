from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import auth.helper as auth_helper
import features.dashboard.api as dashboard_api

from components import page_shell, status_badge, fmt_date, map_component
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════

@rt("/dashboard")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    try:
        stats = await dashboard_api.get_dashboard_stats(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        stats = {}
    except Exception:
        stats = {}

    by_status = stats.get("by_status", {})
    total = stats.get("total_devices", 0)
    pct = round((by_status.get("operational", 0) / total) * 100) if total else 0

    stat_cards = Div(
        Div(
            Div("Total devices", cls="stat-label"),
            Div(str(total), cls="stat-num"),
            Div(style=f"height:3px;background:var(--c-bg-2);border-radius:2px;margin:8px 0 3px;overflow:hidden;",
                children=[Div(style=f"width:{pct}%;height:100%;background:var(--c-green);border-radius:2px;")]),
            Div(f"{pct}% operational", cls="stat-sub"),
            cls="stat-card"
        ),
        Div(Div("Operational", cls="stat-label"),
            Div(str(by_status.get("operational", 0)), cls="stat-num"), cls="stat-card g"),
        Div(Div("Maintenance", cls="stat-label"),
            Div(str(by_status.get("maintenance", 0)), cls="stat-num"), cls="stat-card a"),
        Div(Div("Fault / down", cls="stat-label"),
            Div(str(by_status.get("fault", 0)), cls="stat-num"), cls="stat-card r"),
        Div(Div("Maint. overdue", cls="stat-label"),
            Div(str(stats.get("maintenance_overdue", 0)), cls="stat-num"),
            Div("Needs attention", cls="stat-sub"), cls="stat-card a"),
        Div(Div("Due in 30 days", cls="stat-label"),
            Div(str(stats.get("maintenance_due_soon", 0)), cls="stat-num"),
            Div("Scheduled soon", cls="stat-sub"), cls="stat-card"),
        cls="stat-grid"
    )

    # Open faults
    fault_rows = []
    for f in stats.get("open_faults", []):
        device = f.get("devices") or {}
        fault_rows.append(
            Div(
                Div(
                    Div(device.get("name", "Unknown"), style="font-size:0.875rem;font-weight:500;color:var(--c-text);"),
                    Div(device.get("location", ""), style="font-size:0.75rem;color:var(--c-text-3);"),
                    Div(f.get("description", "")[:80], style="font-size:0.8rem;color:var(--c-text-3);margin-top:2px;"),
                ),
                Div(status_badge(f.get("severity", "medium"), "severity"),
                    Div(fmt_date(f.get("reported_at", "")),
                        style="font-size:0.72rem;color:var(--c-text-3);margin-top:3px;"),
                    style="text-align:right;flex-shrink:0;"),
                style="display:flex;justify-content:space-between;gap:10px;padding:9px 0;border-bottom:1px solid var(--c-border);"
            )
        )

    # Recent maintenance
    maint_rows = []
    for m in stats.get("recent_maintenance", []):
        device = m.get("devices") or {}
        color = "var(--c-green)" if m.get("type") == "preventive" else "var(--c-amber)"
        maint_rows.append(
            Div(
                Div(style=f"width:7px;height:7px;border-radius:50%;background:{color};flex-shrink:0;"),
                Div(
                    Div(device.get("name", "—"), style="font-size:0.875rem;font-weight:500;color:var(--c-text);"),
                    Div(f"{m.get('type', '')} · {fmt_date(m.get('performed_at', ''))}",
                        style="font-size:0.75rem;color:var(--c-text-3);"),
                ),
                style="display:flex;align-items:center;gap:10px;"
            )
        )

    two_col = Div(
        Div(
            H3("Open fault reports", style="margin-bottom:12px;"),
            *fault_rows if fault_rows else [P("No open faults.", style="color:var(--c-text-3);padding:16px 0;")],
            cls="card"
        ),
        Div(
            H3("Recent maintenance", style="margin-bottom:12px;"),
            *maint_rows if maint_rows else [P("No maintenance logged yet.", style="color:var(--c-text-3);padding:16px 0;")],
            cls="card"
        ),
        cls="two-col"
    )

    content = Div(
        Div(
            Div(H1("Dashboard"), P("Overview of your equipment fleet", style="color:var(--c-text-3);")),
            A("+ Add device", href="/devices/new", cls="btn btn-primary"),
            cls="page-header"
        ),
        stat_cards,
        two_col,
        map_component(lat=0.3476, lng=32.5825, markers=[
            {"lat": 0.3476, "lng": 32.5825, "title": "Mulago Hospital"},
            {"lat": 0.3200, "lng": 32.5700, "title": "Clinic B"},
        ]),
    )

    return page_shell(content, current="/dashboard", title="Dashboard — FixMyMedTech")


# ── Root redirect ─────────────────────────────────────────────
@rt("/")
async def get(req):
    return RedirectResponse(
        "/dashboard" if auth_helper.get_token(req) else "/login",
        status_code=302
    )