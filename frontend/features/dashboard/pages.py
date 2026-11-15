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

from i18n import t as make_t
from components import page_shell, status_badge, fmt_date, map_component, lucide, current_user_ctx
from features.devices.cmms_ui import CMMS_CSS, device_wall, needs_list
from datetime import date
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════

@rt("/dashboard")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

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

    try:
        devices = await devices_api.get_devices(token)
    except Exception:
        devices = []

    markers = [
        {
            "lat": d["latitude"],
            "lng": d["longitude"],
            "title": " · ".join(p for p in (d.get("name", ""), d.get("location", "")) if p),
        }
        for d in devices
        if d.get("latitude") is not None and d.get("longitude") is not None
    ]

    stat_cards = Div(
        Div(
            Div(_("dashboard.total_devices"), cls="stat-label"),
            Div(str(total), cls="stat-num"),
            Div(style=f"height:3px;background:var(--c-bg-2);border-radius:2px;margin:8px 0 3px;overflow:hidden;",
                children=[Div(style=f"width:{pct}%;height:100%;background:var(--c-green);border-radius:2px;")]),
            Div(f'{pct}{_("dashboard.pct_operational")}', cls="stat-sub"),
            cls="stat-card"
        ),
        Div(Div(_("dashboard.operational"), cls="stat-label"),
            Div(str(by_status.get("operational", 0)), cls="stat-num"), cls="stat-card g"),
        Div(Div(_("dashboard.maintenance"), cls="stat-label"),
            Div(str(by_status.get("maintenance", 0)), cls="stat-num"), cls="stat-card a"),
        Div(Div(_("dashboard.fault_down"), cls="stat-label"),
            Div(str(by_status.get("fault", 0)), cls="stat-num"), cls="stat-card r"),
        Div(Div(_("dashboard.maint_overdue"), cls="stat-label"),
            Div(str(stats.get("maintenance_overdue", 0)), cls="stat-num"),
            Div(_("dashboard.needs_attention"), cls="stat-sub"), cls="stat-card a"),
        Div(Div(_("dashboard.due_30"), cls="stat-label"),
            Div(str(stats.get("maintenance_due_soon", 0)), cls="stat-num"),
            Div(_("dashboard.scheduled_soon"), cls="stat-sub"), cls="stat-card"),
        cls="stat-grid"
    )

    # Open faults
    fault_rows = []
    for f in stats.get("open_faults", []):
        device = {"name": f.get("device_name"), "location": f.get("device_location")}
        fault_rows.append(
            Div(
                Div(
                    Div(device.get("name", _("dashboard.unknown")), style="font-size:0.875rem;font-weight:500;color:var(--c-text);"),
                    Div(device.get("location", ""), style="font-size:0.75rem;color:var(--c-text-3);"),
                    Div(f.get("description", "")[:80], style="font-size:0.8rem;color:var(--c-text-3);margin-top:2px;"),
                ),
                Div(status_badge(f.get("severity", "medium"), "severity", lang=lang),
                    Div(fmt_date(f.get("reported_at", "")),
                        style="font-size:0.72rem;color:var(--c-text-3);margin-top:3px;"),
                    style="text-align:right;flex-shrink:0;"),
                style="display:flex;justify-content:space-between;gap:10px;padding:9px 0;border-bottom:1px solid var(--c-border);"
            )
        )

    # Recent maintenance
    maint_rows = []
    for m in stats.get("recent_maintenance", []):
        device = {"name": m.get("device_name")}
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
            H3(_("dashboard.open_faults"), style="margin-bottom:12px;"),
            *fault_rows if fault_rows else [P(_("dashboard.no_faults"), style="color:var(--c-text-3);padding:16px 0;")],
            cls="card"
        ),
        Div(
            H3(_("dashboard.recent_maint"), style="margin-bottom:12px;"),
            *maint_rows if maint_rows else [P(_("dashboard.no_maint"), style="color:var(--c-text-3);padding:16px 0;")],
            cls="card"
        ),
        cls="two-col"
    )

    active = [d for d in devices if d.get("status") != "decommissioned"]
    needs = Div(
        Div(Span(lucide("flag"), cls="sec-ico danger" if stats.get("needs_you_total") else "sec-ico ok"),
            H2(_("cmms.needs_today")),
            Span(_("cmms.needs_count").format(n=stats.get("needs_you_total", 0)),
                 cls="badge badge-danger" if stats.get("needs_you_total") else "badge badge-ok"),
            cls="sec-h"),
        needs_list(_, stats.get("needs_you", []), stats.get("needs_you_total", 0), lang),
        cls="card", style="margin-bottom:16px;", id="needs",
    )
    wall = Div(
        Div(Span(lucide("devices"), cls="sec-ico"), H2(_("cmms.wall_title")),
            A(_("cmms.all_devices"), href="/devices", cls="side"),
            cls="sec-h"),
        device_wall(_, active, date.today().isoformat()),
        cls="card", style="margin-bottom:16px;",
    )
    numbers = Details(
        Summary(_("cmms.numbers"), Span(f'{total} · {pct}{_("dashboard.pct_operational")}',
                style="font-weight:400;font-size:12px;color:var(--text-muted);margin-left:auto;")),
        stat_cards,
        two_col,
        map_component(lat=0.3476, lng=32.5825, markers=markers, fit=True) if markers else "",
        cls="more",
    )

    # Hero (platform brief): a greeting, one line with the share of working
    # devices, and four "pieces" that open the device list on that status.
    words = (current_user_ctx().get("name") or "").split()
    # "Dr. Amina Okello" → "Dr. Amina"; "Amina Okello" → "Amina".
    first = " ".join(words[:2] if words and words[0].endswith(".") else words[:1])
    def piece(icon, tone, num, label, href):
        return A(Div(Span(lucide(icon), cls=f"dot {tone}"), B(str(num)), cls="piece-top"),
                 Small(label), href=href, cls="piece")
    hero = Div(
        Div(
            Div(Div(_("dash.hero_eyebrow"), cls="hero-eyebrow"),
                H1(_("dash.hero_hi").format(name=first) if first else _("dash.hero_hi_anon")),
                P(_("dash.hero_line").format(pct=pct, n=total) if total else _("dash.hero_empty"))),
            A(lucide("plus"), _("dashboard.add_device").lstrip("+ "), href="/new_device", cls="btn btn-light")
            if auth_helper.adds_devices(req) else "",
            cls="hero-top",
        ),
        Div(Span(style=f"width:{pct}%"), cls="meter", role="img",
            aria_label=f'{pct}{_("dashboard.pct_operational")}') if total else "",
        Div(
            piece("check", "ok", by_status.get("operational", 0), _("dash.piece_working"), "/devices?status=operational"),
            piece("wrench", "warn", by_status.get("maintenance", 0), _("dash.piece_service"), "/devices?status=maintenance"),
            piece("faults", "danger", by_status.get("fault", 0), _("dash.piece_fault"), "/devices?status=fault"),
            piece("calendar", "warn", stats.get("maintenance_overdue", 0), _("dash.piece_overdue"), "#needs"),
            cls="pieces",
        ) if total else "",
        cls="hero",
    )

    # Community hub: the Equipment world's next step (clinic accounts).
    from features.community.hub import next_step_block
    next_step = await next_step_block(req, token, "equipment", _, total_devices=total if stats else None)

    content = Div(
        Style(CMMS_CSS),
        next_step,
        hero,
        needs,
        wall,
        numbers,
    )

    return page_shell(content, current="/dashboard", title=_("title.dashboard"), lang=lang)