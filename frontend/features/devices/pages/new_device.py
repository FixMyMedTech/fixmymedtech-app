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
        title = content.get('title')
        cat_options.append(Option(f"{icon} {title}", value=g["slug"],
                                  data_first=(title or "").split()[0] if title else ""))
    other_label = CATEGORY_FALLBACKS.get("other", {}).get(lang, "Other")
    cat_options.append(Option(f"🏥 {other_label}", value="other",
                              data_first=(other_label or "").split()[0] if other_label else ""))

    try:
        orgs = await org_api.get_my_organizations(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        raise
    org_options = [Option(o["name"], value=o["id"]) for o in orgs]

    form = Form(
        A(_("new_device.back"), href="/devices",
        style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:20px;display:inline-block;"),
        H1(_("new_device.add_heading"), style="margin-bottom:4px;"),
        P(_("new_device.add_desc"), style="margin-bottom:20px;"),
        Div(
            H3(_("new_device.basic_info"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label(_("new_device.category_label"), cls="label", for_="category"),
                    Select(*cat_options, id="category", name="category_id", cls="input",
                        onchange="autoName()"),
                    cls="form-group"),
                Div(Label(_("new_device.manufacturer_label"), cls="label", for_="manufacturer"),
                    Input(id="manufacturer", name="manufacturer", cls="input",
                        placeholder=_("new_device.manufacturer_placeholder"),
                        oninput="autoName()"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.model_label"), cls="label", for_="model"),
                    Input(id="model", name="model", cls="input",
                        placeholder=_("new_device.model_placeholder"),
                        oninput="autoName()"),
                    cls="form-group"),
                Div(Label(_("new_device.serial_label"), cls="label"),
                    Input(name="serial_number", cls="input", placeholder=_("new_device.serial_placeholder")),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.name_label"), cls="label", for_="device-name"),
                    Input(id="device-name", name="name", value=_("new_device.name_unknown"),
                        cls="input", oninput="onNameEdited()",
                        data_unknown=_("new_device.name_unknown")),
                    cls="form-group"),
                Div(Label(_("new_device.year_label"), cls="label"),
                    Input(name="manufacture_year", type="number", cls="input",
                        placeholder=_("new_device.year_placeholder"), min="1990", max="2030"),
                    cls="form-group"),
                Script("""
                let nameEdited = false;
                function onNameEdited() { nameEdited = true; }
                function autoName() {
                    if (nameEdited) return;
                    const cat = document.getElementById('category').selectedOptions[0];
                    const cw = (cat && cat.dataset.first) ? cat.dataset.first.trim() : '';
                    const m = document.getElementById('manufacturer').value.trim();
                    const mo = document.getElementById('model').value.trim();
                    const input = document.getElementById('device-name');
                    input.value = [cw, m, mo].filter(Boolean).join(' ') || input.dataset.unknown;
                }
                """),
                cls="form-row"
            ),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            H3(_("new_device.photo"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            P(_("new_device.photo_desc"), style="font-size:0.85rem;color:var(--c-text-3);margin-bottom:14px;"),
            Div(
                Div(
                    Button(_("new_device.photo_take_label"), type="button", id="open-camera",
                           cls="btn btn-secondary", onclick="openCamera()"),
                    Button(_("new_device.photo_capture_label"), type="button", id="capture-photo",
                           cls="btn btn-primary", style="display:none;", onclick="capturePhoto()"),
                    Button(_("new_device.photo_close_label"), type="button", id="close-camera",
                           cls="btn btn-secondary", style="display:none;", onclick="stopCamera()"),
                    style="display:flex;gap:10px;margin-bottom:10px;"
                ),
                Video(id="camera-view", autoplay=True, playsinline=True, muted=True,
                      style="display:none;width:100%;max-height:280px;border-radius:8px;margin-bottom:10px;background:#000;"),
                Div(
                    Div(Label(_("new_device.photo_choose_label"), cls="label", for_="photo-file"),
                        Input(type="file", id="photo-file", name="photo",
                              accept="image/*", cls="input",
                              onchange="previewPhoto(this)"),
                        cls="form-group"),
                ),
                Div(
                    Img(id="photo-preview", alt="", style="display:none;max-width:100%;max-height:220px;border-radius:8px;margin-top:10px;"),
                    style="text-align:center;"
                ),
                Script("""
                let cameraStream = null;

                function openCamera() {
                    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                        alert('Camera not supported in this browser');
                        return;
                    }
                    navigator.mediaDevices.getUserMedia({
                        video: { facingMode: { ideal: 'environment' } },
                        audio: false
                    }).then((stream) => {
                        cameraStream = stream;
                        const video = document.getElementById('camera-view');
                        video.srcObject = stream;
                        video.style.display = 'block';
                        video.play();
                        document.getElementById('open-camera').style.display = 'none';
                        document.getElementById('capture-photo').style.display = 'inline-block';
                        document.getElementById('close-camera').style.display = 'inline-block';
                    }).catch((err) => alert('Camera error: ' + err.message));
                }

                function stopCamera() {
                    if (cameraStream) {
                        cameraStream.getTracks().forEach(function (t) { t.stop(); });
                        cameraStream = null;
                    }
                    const video = document.getElementById('camera-view');
                    video.srcObject = null;
                    video.style.display = 'none';
                    document.getElementById('open-camera').style.display = 'inline-block';
                    document.getElementById('capture-photo').style.display = 'none';
                    document.getElementById('close-camera').style.display = 'none';
                }

                function capturePhoto() {
                    const video = document.getElementById('camera-view');
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    canvas.toBlob(function (blob) {
                        if (!blob) return;
                        const file = new File([blob], 'camera_photo.jpg', { type: blob.type || 'image/jpeg' });
                        const dt = new DataTransfer();
                        dt.items.add(file);
                        document.getElementById('photo-file').files = dt.files;
                        const img = document.getElementById('photo-preview');
                        img.src = URL.createObjectURL(blob);
                        img.style.display = 'inline-block';
                        stopCamera();
                    }, 'image/jpeg', 0.92);
                }

                function previewPhoto(input) {
                    if (input.files && input.files[0]) {
                        const img = document.getElementById('photo-preview');
                        const reader = new FileReader();
                        reader.onload = function (e) {
                            img.src = e.target.result;
                            img.style.display = 'inline-block';
                        };
                        reader.readAsDataURL(input.files[0]);
                    }
                }
                """),
                cls="form-group",
            ),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            H3(_("new_device.location_acquisition"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label(_("new_device.org_label"), cls="label", for_="organization_id"),
                    Select(*org_options, id="organization_id", name="organization_id", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
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
        enctype="multipart/form-data",
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
async def post(req, device_id: str):
    token, redirect =  auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    form = await req.form()

    def field(name: str) -> str:
        v = form.get(name)
        return "" if v is None else str(v)

    name = field("name").strip()
    if not name:
        from features.devices.static.guides import GUIDES, CATEGORY_FALLBACKS
        cat_slug = field("category_id")
        cat_first = ""
        if cat_slug:
            guide = {g["slug"]: g for g in GUIDES}.get(cat_slug)
            title = (guide.get(lang) or guide).get("title") if guide else CATEGORY_FALLBACKS.get(cat_slug, {}).get(lang, "Other")
            cat_first = (title or "").split()[0]
        name = " ".join(x for x in [cat_first, field("manufacturer").strip(), field("model").strip()] if x)
    payload = {"name": name or _("new_device.name_unknown")}
    if device_id:         payload["id"]        = device_id
    if field("organization_id"): payload["organization_id"]  = field("organization_id")
    if field("manufacturer"):    payload["manufacturer"]     = field("manufacturer")
    if field("model"):           payload["model"]            = field("model")
    if field("serial_number"):   payload["serial_number"]    = field("serial_number")
    if field("category_id"):     payload["category_id"]      = field("category_id")
    if field("location"):        payload["location"]         = field("location")
    if field("acquisition_type"):payload["acquisition_type"] = field("acquisition_type")
    if field("acquisition_date"):payload["acquisition_date"] = field("acquisition_date")
    if field("next_maintenance"):payload["next_maintenance"] = field("next_maintenance")
    if field("notes"):           payload["notes"]            = field("notes")

    try:
        if field("manufacture_year"):
            payload["manufacture_year"] = int(field("manufacture_year"))
        if field("latitude"):
            payload["latitude"] = float(field("latitude"))
        if field("longitude"):
            payload["longitude"] = float(field("longitude"))
        await devices_api.create_device(token, payload)

        # Optionally upload a photo (camera capture or file picker) to MinIO.
        photo = form.get("photo") or form.get("photo_camera")
        if photo is not None and getattr(photo, "filename", ""):
            photo_data = await photo.read()
            if photo_data:
                await devices_api.upload_device_photo(
                    token, device_id,
                    photo.filename or "device_photo.jpg",
                    photo_data,
                    photo.content_type,
                )
        return RedirectResponse(f"/device/{device_id}", status_code=303)
    except Exception:
        return RedirectResponse(f"/device/{device_id}/new", status_code=303)
