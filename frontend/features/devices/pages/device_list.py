from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api
import features.groups.api as org_api

from components import page_shell, status_badge, fmt_date
from features.devices.static.guides import category_label
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# DEVICES LIST
# ══════════════════════════════════════════════════════════════

@rt("/devices")
async def get(req, status: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        devices = await devices_api.get_devices(token, status or None)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        if e.response.status_code == 403:
            return page_shell(
                Div(
                    Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                    H2(_("device_list.access_denied")),
                    P(_("device_list.access_msg")),
                    style="text-align:center;padding:60px 24px;"
                ),
                lang=lang
            )
        devices = []
    except Exception:
        devices = []

    status_filters = [
        ("", _("device_list.filter_all")),
        ("operational", _("device_list.filter_operational")),
        ("maintenance", _("device_list.filter_maintenance")),
        ("fault", _("device_list.filter_fault")),
        ("decommissioned", _("device_list.filter_decommissioned")),
    ]

    is_admin = False
    my_org_ids = set()
    try:
        me = await auth_api.get_me(token)
        my_orgs = me.get("organizations", [])
        my_org_ids = {o["id"] for o in my_orgs}
        is_admin = any(o.get("role") == "admin" for o in my_orgs)
    except Exception:
        is_admin = False

    orgs = []
    try:
        orgs = await org_api.get_organizations()
    except Exception:
        orgs = []

    pills = [
        A(label, href=f"/devices?status={val}",
        cls=f"pill {'active' if status == val else ''}")
        for val, label in status_filters
    ]

    def maintenance_cell(d):
        name = (d.get("organization_maintenance") or {}).get("name", "")
        owns = d.get("organization_id") in my_org_ids
        if not (is_admin and owns):
            return Td(Span(name, style="font-size:0.875rem;"))
        options = [
            Option(f"{o['name']} ({o['country']})", value=o["id"],
                   selected=(o["id"] == d.get("organization_maintenance_id")))
            for o in orgs
        ]
        return Td(
            Form(
                Select(
                    *options,
                    name="organization_maintenance_id",
                    onchange="this.form.submit()",
                    style="max-width:220px;padding:6px 8px;border:1px solid var(--c-border);border-radius:var(--r-md);font-size:0.8rem;",
                ),
                method="post",
                action=f"/devices/{d['id']}/maintenance-org",
            )
        )

    rows = []
    for d in devices:
        cat = d.get("category") or {}
        nm = d.get("next_maintenance", "")
        overdue = nm and nm < __import__("datetime").datetime.now().isoformat()
        rows.append(Tr(
            Td(Div(d.get("name", ""), style="font-weight:500;font-size:0.875rem;color:var(--c-text);"),
            Div(f"{d.get('manufacturer','')} {d.get('model','')}".strip(),
                style="font-size:0.75rem;color:var(--c-text-3);")),
            Td(f"{cat.get('icon','🏥')} {category_label(cat, lang)}", style="font-size:0.875rem;"),
            Td(d.get("location", _("common.fallback")), style="font-size:0.875rem;"),
            Td(status_badge(d.get("status", "operational"), lang=lang)),
            Td(
                Span(fmt_date(nm), cls="overdue" if overdue else ""),
                Span(_("device_list.overdue"), cls="overdue-tag") if overdue else ""
            ),
            maintenance_cell(d),
            Td(A(_("device_list.view"), href=f"/device/{d['id']}", cls="btn btn-secondary btn-sm")),
        ))

    table = Div(
        Table(
            Thead(Tr(Th(_("device_list.col_device")), Th(_("device_list.col_category")), Th(_("device_list.col_location")),
                    Th(_("device_list.col_status")), Th(_("device_list.col_next")), Th(_("device_list.col_maintenance_org")), Th(""))),
            Tbody(*rows) if rows else Tbody(
                Tr(Td(_("device_list.empty"), colspan="7",
                    style="text-align:center;padding:32px;color:var(--c-text-3);"))
            )
        ),
        cls="table-wrap"
    )

    content = Div(
        Div(
            Div(H1(_("device_list.title")), P(f"{len(devices)} {_('device_list.device') if len(devices)==1 else _('device_list.device') + _('device_list.devices_plural')} {_('device_list.registered')}",
                                style="color:var(--c-text-3);")),
            A(_("device_list.add"), href="/new_device", cls="btn btn-primary"),
            cls="page-header"
        ),
        Div(*pills, cls="toolbar"),
        table,
    )

    return page_shell(content, current="/devices", title=_("title.devices"), lang=lang)


@rt("/devices/{device_id}/maintenance-org")
async def post_maintenance_org(req, device_id: str, organization_maintenance_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    try:
        await devices_api.update_device(token, device_id, {"organization_maintenance_id": organization_maintenance_id})
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
    return RedirectResponse("/devices", status_code=303)
