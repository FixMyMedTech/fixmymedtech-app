from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.devices.api as devices_api

from components import page_shell, status_badge, fmt_date, map_component
from features.devices.static.guides import category_label
from i18n import t as make_t
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# DEVICE DETAIL
# ══════════════════════════════════════════════════════════════


@rt("/device/{device_id}/location")
async def post_location(req, device_id: str, latitude: float = 0, longitude: float = 0):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    try:
        await devices_api.update_location_device(token, device_id, {"latitude": latitude, "longitude": longitude})
    except Exception:
        pass
    return RedirectResponse(f"/device/{device_id}", status_code=303)


@rt("/device/{device_id}")
async def get(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        data = await devices_api.get_device(token, device_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse(f"/device/{device_id}", status_code=302)
    except Exception:
        return RedirectResponse(f"/device/{device_id}", status_code=302)

    d = data.get("device", {})
    cat = d.get("category") or {}
    org = d.get("organization") or {}
    logs = data.get("maintenance_logs", [])
    faults = data.get("fault_reports", [])
    docs = data.get("documents", [])

    qr_url = f"{req.base_url}d/{device_id}"

    # Maintenance log rows
    log_rows = [
        Tr(
            Td(fmt_date(l.get("performed_at", "")), style="font-size:0.875rem;"),
            Td(Span(l.get("type",""), cls="badge badge-blue")),
            Td(l.get("description",_("common.fallback")), style="font-size:0.875rem;"),
            Td((l.get("performed_by_profile") or {}).get("full_name",_("common.fallback")), style="font-size:0.875rem;"),
            Td(f"${l['cost_usd']}" if l.get("cost_usd") else _("common.fallback"), style="font-size:0.875rem;"),
            Td(A(_("device_list.view"), href=f"/device/{device_id}/log/{l['id']}",
                 cls="btn btn-secondary btn-sm")),
        ) for l in logs
    ]

    # Fault rows
    fault_rows = [
        Tr(
            Td(fmt_date(f.get("reported_at","")), style="font-size:0.875rem;"),
            Td(f.get("reporter_name",_("common.fallback")), style="font-size:0.875rem;"),
            Td(f.get("description",""), style="font-size:0.875rem;"),
            Td(status_badge(f.get("severity","medium"), "severity", lang=lang)),
            Td(status_badge(f.get("status","open"), "fault", lang=lang)),
            Td(A(_("device_list.view"), href=f"/device/{device_id}/fault/{f['id']}",
                 cls="btn btn-secondary btn-sm")),
        ) for f in faults
    ]

    content = Div(
        A(_("device_detail.back"), href="/devices",
        style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:14px;display:inline-block;"),
        Div(
            Div(
                Div(f"{cat.get('icon','🏥')} {category_label(cat, lang)}",
                    style="font-size:0.8rem;color:var(--c-text-3);margin-bottom:4px;"),
                H1(d.get("name",""), style="margin-bottom:4px;"),
                P(f"{d.get('manufacturer','')} {d.get('model','')} · {d.get('location',_('device_detail.no_location'))}",
                style="color:var(--c-text-3);"),
            ),
            Div(status_badge(d.get("status","operational"), lang=lang),
                style="flex-shrink:0;"),
            cls="page-header", style="margin-bottom:14px;"
        ),
        # QR banner
        Div(
            Span("▣", style="font-size:1.3rem;"),
            Div(
                Div(_("device_detail.public_qr"), style="font-size:0.75rem;font-weight:500;color:var(--c-primary);"),
                A(qr_url, href=qr_url, target="_blank",
                style="font-size:0.8rem;color:var(--c-primary-md);font-family:monospace;"),
            ),
            style="display:flex;align-items:center;gap:12px;background:var(--c-primary-lt);border:1px solid #a7d9ce;border-radius:var(--r-md);padding:12px 16px;margin-bottom:20px;"
        ),
        # Device info
        Div(
            Div(
                H3(_("device_detail.info"), style="margin-bottom:12px;"),
                Dl(
                    *[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;")
                    for k, v in [
                        (_("device_detail.serial"), d.get("serial_number",_("common.fallback"))),
                        (_("device_detail.manufacturer"),  d.get("manufacturer",_("common.fallback"))),
                        (_("device_detail.model"),         d.get("model",_("common.fallback"))),
                        (_("device_detail.year"),          str(d.get("manufacture_year",_("common.fallback")))),
                        (_("device_detail.acquisition"),   f"{d.get('acquisition_type',_('common.fallback'))} · {fmt_date(d.get('acquisition_date',''))}"),
                        (_("device_detail.location"),      d.get("location",_("common.fallback"))),
                        (_("device_detail.organisation"),  org.get("name",_("common.fallback"))),
                    ]]
                ),
                cls="card"
            ),
            Div(
                H3(_("device_detail.maintenance"), style="margin-bottom:12px;"),
                Dl(
                    *[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;")
                    for k, v in [
                        (_("device_detail.last_maint"), fmt_date(d.get("last_maintenance",""))),
                        (_("device_detail.next_maint"), fmt_date(d.get("next_maintenance",""))),
                    ]]
                ),
                cls="card"
            ),
            cls="two-col", style="margin-bottom:16px;"
        ),
        # Map
        Div(
            H3(_("device_detail.location_map"), style="margin-bottom:12px;"),
            map_component(
                lat=d.get("latitude", 0),
                lng=d.get("longitude", 0),
                markers=[{"lat": d["latitude"], "lng": d["longitude"], "title": d.get("name","")}],
                height="300px"
            ) if d.get("latitude") is not None and d.get("longitude") is not None else "",
            Form(
                Input(type="hidden", id="loc-lat", name="latitude"),
                Input(type="hidden", id="loc-lng", name="longitude"),
                Button(
                    "📍 " + _("device_detail.capture_location"),
                    type="button", cls="btn btn-secondary btn-sm",
                    onclick="getLocation()",
                    style="margin-top:8px;"
                ),
                Script("""
                function getLocation() {
                    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
                    navigator.geolocation.getCurrentPosition((pos) => {
                        document.getElementById('loc-lat').value = pos.coords.latitude;
                        document.getElementById('loc-lng').value = pos.coords.longitude;
                        document.getElementById('loc-form').submit();
                    }, (err) => alert('Geolocation error: ' + err.message));
                }
                """),
                id="loc-form",
                method="post", action=f"/device/{device_id}/location",
            ),
            cls="card", style="margin-bottom:16px;"
        ),
        # Maintenance logs
        Div(
            H3(_("device_detail.history"), style="margin-bottom:12px;"),
            Div(
                Table(
                    Thead(Tr(Th(_("device_detail.col_date")), Th(_("device_detail.col_type")), Th(_("device_detail.col_description")), Th(_("device_detail.col_technician")), Th(_("device_detail.col_cost")), Th(""))),
                    Tbody(*log_rows) if log_rows else Tbody(
                        Tr(Td(_("device_detail.no_maint"), colspan="6",
                            style="color:var(--c-text-3);padding:20px;text-align:center;")))
                ),
                style="border:none;border-radius:0;"
            ),
            cls="card", style="margin-bottom:16px;"
        ),
        # Fault reports
        Div(
            H3(_("device_detail.faults"), style="margin-bottom:12px;"),
            Div(
                Table(
                    Thead(Tr(Th(_("device_detail.col_date")), Th(_("device_detail.col_reported_by")), Th(_("device_detail.col_description")), Th(_("device_detail.col_severity")), Th(_("device_detail.col_status")), Th(""))),
                    Tbody(*fault_rows) if fault_rows else Tbody(
                        Tr(Td(_("device_detail.no_faults"), colspan="6",
                            style="color:var(--c-text-3);padding:20px;text-align:center;")))
                ),
                style="border:none;border-radius:0;"
            ),
            cls="card"
        ),
    )

    return page_shell(content, current="/devices", lang=lang, title=f"{d.get('name',_('common.device'))}{_('title.device_detail')}")

