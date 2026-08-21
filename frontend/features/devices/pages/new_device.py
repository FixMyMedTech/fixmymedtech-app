from urllib.parse import urlparse

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
import features.groups.api as org_api

from components import *

from i18n import t as make_t

from components import page_shell, status_badge, fmt_date
rt = APIRouter()
# ══════════════════════════════════════════════════════════════
# NEW DEVICE
# ══════════════════════════════════════════════════════════════


@rt("/new_device")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        org = await org_api.get_my_organizations(token)

        content = Div(
                Div(
                    Script(src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"),
                    Div("📸", style="width:56px;height:56px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
                    H2(_("new_device.scan_heading")),
                    P(_("new_device.scan_desc"), style="margin-top:8px;"),
                    qr_scanner_component(target_url="/scan-result"),
                    style="text-align:center;padding:60px 40px;"
                ),
                style="max-width:440px;margin:80px auto;"
            )
        
        return page_shell(content, current="/new_device", title=_("title.new_device"), lang=lang)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return page_shell(
                Div(
                    Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                    H2(_("new_device.access_denied")),
                    P(_("new_device.access_msg")),
                    style="text-align:center;padding:60px 24px;"
                ),
                current="/new_device",
                title=_("title.new_device"),
                lang=lang
            )
    except Exception:
        return page_shell(
                Div(
                    Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                    H2(_("new_device.access_denied")),
                    P(_("new_device.access_msg")),
                    style="text-align:center;padding:60px 24px;"
                ),
                current="/new_device",
                title=_("title.new_device"),
                lang=lang
            )

@rt("/scan-result")
async def get(req, code: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    parsed = urlparse(code)
    parts = [p for p in parsed.path.split("/") if p]
    device_id = parts[-1] if parts else code

    try:
        existing = await devices_api.get_device_public(device_id)
        if existing:
            d = existing.get("device", {})
            content = Div(
                Div("✅", style="width:56px;height:56px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
                H2(_("new_device.already_heading")),
                P(_("new_device.already_msg"), style="margin-top:8px;"),
                Div(
                    A(_("new_device.view_device"), href=f"/d/{device_id}", cls="btn btn-primary"),
                    A(_("new_device.scan_another"), href="/new_device", cls="btn btn-secondary"),
                    style="display:flex;gap:10px;justify-content:center;margin-top:20px;"
                ),
                Form(
                    Input(type="hidden", id="loc-lat", name="latitude"),
                    Input(type="hidden", id="loc-lng", name="longitude"),
                    Button(
                        "📍 " + _("new_device.capture_location"),
                        type="button", cls="btn btn-secondary btn-sm",
                        onclick="getLocation()",
                        style="margin-top:16px;"
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
                ) if d.get("latitude") is None or d.get("longitude") is None else "",
                style="text-align:center;padding:60px 40px;"
            )
            return page_shell(content, current="/new_device", title=_("title.already_registered"), lang=lang)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 422):
            return RedirectResponse(f"/device/{device_id}/new")
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)

    return RedirectResponse(f"/device/{device_id}/new")


@rt("/device/{device_id}/new")
async def get(req,device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        await devices_api.get_device_public(device_id)
        return RedirectResponse(f"/device/{device_id}", status_code=303)
    except httpx.HTTPStatusError as e:
        if e.response.status_code not in (404, 422):
            raise
    except Exception:
        pass

    from features.devices.static.guides import GUIDES, CATEGORY_ICONS, CATEGORY_FALLBACKS

    cat_options = [Option(_("new_device.category_placeholder"), value="")]
    for g in GUIDES:
        content = g.get(lang) or g
        icon = CATEGORY_ICONS.get(g["slug"], "🏥")
        cat_options.append(Option(f"{icon} {content.get('title')}", value=g["slug"]))
    other_label = CATEGORY_FALLBACKS.get("other", {}).get(lang, "Other")
    cat_options.append(Option(f"🏥 {other_label}", value="other"))

    orgs = await org_api.get_my_organizations(token)
    org_options = [Option(o["name"], value=o["id"]) for o in orgs]

    form = Form(
        A(_("new_device.back"), href="/devices",
        style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:20px;display:inline-block;"),
        H1(_("new_device.add_heading"), style="margin-bottom:4px;"),
        P(_("new_device.add_desc"), style="margin-bottom:20px;"),
        Div(
            H3(_("new_device.basic_info"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label(_("new_device.org_label"), cls="label", for_="organization_id"),
                    Select(*org_options, id="organization_id", name="organization_id", cls="input"),
                    cls="form-group"),
                Div(Label(_("new_device.category_label"), cls="label", for_="category"),
                    Select(*cat_options, id="category", name="category_id", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.name_label"), cls="label", for_="name"),
                    Input(id="name", name="name", cls="input", placeholder=_("new_device.name_placeholder")),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.manufacturer_label"), cls="label"),
                    Input(name="manufacturer", cls="input", placeholder=_("new_device.manufacturer_placeholder")),
                    cls="form-group"),
                Div(Label(_("new_device.model_label"), cls="label"),
                    Input(name="model", cls="input", placeholder=_("new_device.model_placeholder")),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.serial_label"), cls="label"),
                    Input(name="serial_number", cls="input", placeholder=_("new_device.serial_placeholder")),
                    cls="form-group"),
                Div(Label(_("new_device.year_label"), cls="label"),
                    Input(name="manufacture_year", type="number", cls="input",
                        placeholder=_("new_device.year_placeholder"), min="1990", max="2030"),
                    cls="form-group"),
                cls="form-row"
            ),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            H3(_("new_device.location_acquisition"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label(_("new_device.location_label"), cls="label"),
                    Input(name="location", cls="input", placeholder=_("new_device.location_placeholder")),
                    cls="form-group"),
                Div(Label(_("new_device.acquisition_label"), cls="label"),
                    Select(Option(_("new_device.acquisition_purchased"), value="purchased"),
                        Option(_("new_device.acquisition_donated"), value="donated"),
                        Option(_("new_device.acquisition_leased"), value="leased"),
                        name="acquisition_type", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.acquisition_date"), cls="label"),
                    Input(name="acquisition_date", type="date", cls="input"),
                    cls="form-group"),
                Div(Label(_("new_device.next_maint"), cls="label"),
                    Input(name="next_maintenance", type="date", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Input(type="hidden", id="loc-lat", name="latitude", value=""),
                Input(type="hidden", id="loc-lng", name="longitude", value=""),
                Button(
                    "📍 " + _("new_device.capture_location"),
                    type="button", cls="btn btn-secondary btn-sm",
                    onclick="captureLoc()",
                    style="margin-top:8px;"
                ),
                Script("""
                function captureLoc() {
                    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
                    navigator.geolocation.getCurrentPosition((pos) => {
                        document.getElementById('loc-lat').value = pos.coords.latitude;
                        document.getElementById('loc-lng').value = pos.coords.longitude;
                    }, (err) => alert('Geolocation error: ' + err.message));
                }
                """),
                cls="form-group",
            ),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            H3(_("new_device.notes"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(Textarea(name="notes", cls="input", placeholder=_("new_device.notes_placeholder"), rows="3"),
                cls="form-group"),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            A(_("new_device.cancel"), href="/devices", cls="btn btn-secondary"),
            Button(_("new_device.register"), type="submit", cls="btn btn-primary"),
            style="display:flex;justify-content:flex-end;gap:10px;"
        ),
        method="post", action=f"/device/{device_id}/new",
        style="max-width:720px;"
    )

    return page_shell(form, current=f"/device/{device_id}/new", title=_("title.add_device"), lang=lang)



# @rt("/devices/scan_new")
# async def get(req):
#     token, redirect = auth_helper.require_auth(req)
#     if redirect: return redirect

#     try:
#         categories = await devices_api.get_categories()
#     except Exception:
#         categories = []

#     cat_options = [Option("— Select category —", value="")]
#     cat_options += [Option(f"{c.get('icon','')} {c['name']}", value=c["id"]) for c in categories]

#     form = Form(
#         A("← Devices", href="/devices",
#         style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:20px;display:inline-block;"),
#         H1("Add new device", style="margin-bottom:4px;"),
#         P("Register a medical device to start tracking it", style="margin-bottom:20px;"),
#         Div(
#             H3("Basic information", style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
#             Div(
#                 Div(Label("Device name *", cls="label", for_="name"),
#                     Input(id="name", name="name", cls="input", placeholder="e.g. Ventilator LTV 1200"),
#                     cls="form-group"),
#                 Div(Label("Category", cls="label", for_="category"),
#                     Select(*cat_options, id="category", name="category_id", cls="input"),
#                     cls="form-group"),
#                 cls="form-row"
#             ),
#             Div(
#                 Div(Label("Manufacturer", cls="label"),
#                     Input(name="manufacturer", cls="input", placeholder="e.g. GE Healthcare"),
#                     cls="form-group"),
#                 Div(Label("Model", cls="label"),
#                     Input(name="model", cls="input", placeholder="e.g. ProCare B40"),
#                     cls="form-group"),
#                 cls="form-row"
#             ),
#             Div(
#                 Div(Label("Serial number", cls="label"),
#                     Input(name="serial_number", cls="input", placeholder="SN-XXXXXX"),
#                     cls="form-group"),
#                 Div(Label("Manufacture year", cls="label"),
#                     Input(name="manufacture_year", type="number", cls="input",
#                         placeholder="2018", min="1990", max="2030"),
#                     cls="form-group"),
#                 cls="form-row"
#             ),
#             cls="card", style="margin-bottom:14px;"
#         ),
#         Div(
#             H3("Location & acquisition", style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
#             Div(
#                 Div(Label("Location", cls="label"),
#                     Input(name="location", cls="input", placeholder="e.g. ICU / Bed 4"),
#                     cls="form-group"),
#                 Div(Label("Acquisition type", cls="label"),
#                     Select(Option("Purchased", value="purchased"),
#                         Option("Donated", value="donated"),
#                         Option("Leased", value="leased"),
#                         name="acquisition_type", cls="input"),
#                     cls="form-group"),
#                 cls="form-row"
#             ),
#             Div(
#                 Div(Label("Acquisition date", cls="label"),
#                     Input(name="acquisition_date", type="date", cls="input"),
#                     cls="form-group"),
#                 Div(Label("Next maintenance due", cls="label"),
#                     Input(name="next_maintenance", type="date", cls="input"),
#                     cls="form-group"),
#                 cls="form-row"
#             ),
#             cls="card", style="margin-bottom:14px;"
#         ),
#         Div(
#             H3("Notes", style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
#             Div(Textarea(name="notes", cls="input", placeholder="Any relevant notes…", rows="3"),
#                 cls="form-group"),
#             cls="card", style="margin-bottom:14px;"
#         ),
#         Div(
#             A("Cancel", href="/devices", cls="btn btn-secondary"),
#             Button("Register device", type="submit", cls="btn btn-primary"),
#             style="display:flex;justify-content:flex-end;gap:10px;"
#         ),
#         method="post", action="/devices/new",
#         style="max-width:720px;"
#     )

#     return page_shell(form, current="/devices/new", title="Add device — FixMyMedTech")


@rt("/device/{device_id}/new")
async def post(req, device_id: str, name: str, organization_id: str = "",
            manufacturer: str = "", model: str = "",
            serial_number: str = "", category_id: str = "", location: str = "",
            acquisition_type: str = "purchased", acquisition_date: str = "",
            manufacture_year: str = "", next_maintenance: str = "", notes: str = "",
            latitude: str = "", longitude: str = ""):
    token, redirect =  auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    payload = {"name": name}
    if device_id:         payload["id"]        = device_id
    if organization_id:   payload["organization_id"]  = organization_id
    if manufacturer:      payload["manufacturer"]     = manufacturer
    if model:             payload["model"]            = model
    if serial_number:     payload["serial_number"]    = serial_number
    if category_id:       payload["category_id"]      = category_id
    if location:          payload["location"]         = location
    if acquisition_type:  payload["acquisition_type"] = acquisition_type
    if acquisition_date:  payload["acquisition_date"] = acquisition_date
    if next_maintenance:  payload["next_maintenance"] = next_maintenance
    if notes:             payload["notes"]            = notes

    try:
        if manufacture_year:
            payload["manufacture_year"] = int(manufacture_year)
        if latitude:
            payload["latitude"] = float(latitude)
        if longitude:
            payload["longitude"] = float(longitude)
        await devices_api.create_device(token, payload)
        return RedirectResponse(f"/device/{device_id}", status_code=303)
    except Exception:
        return RedirectResponse(f"/device/{device_id}/new", status_code=303)
