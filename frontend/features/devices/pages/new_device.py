from urllib.parse import quote, urlparse

from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, json, httpx
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
from features.groups.pages.groups_page import GEOLOC_JS, _hs_dialog
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
                    qr_scanner_component(target_url="/scan-result", lang=lang),
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
async def get(req, device_id: str, selected: str = ""):
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

    try:
        orgs = await org_api.get_my_organizations(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        raise

    form = _device_form(lang, device_id, orgs, selected=selected)
    return _build_page(req, lang, device_id, form, orgs,
                       selected=selected)


def _wizard_script(device_id: str, step_tmpl: str):
    js = """
(function () {
    const KEY = @@STEP_KEY@@;
    const TMPL = @@STEP_TMPL@@;
    const stepEls = Array.from(document.querySelectorAll('[data-step]'));
    const total = stepEls.length;
    const form = document.getElementById('device-form');
    const backBtn = document.getElementById('step-back');
    const nextBtn = document.getElementById('step-next');
    const regBtn = document.getElementById('step-register');
    const labelEl = document.getElementById('step-label');
    if (!form || !stepEls.length) return;

    function fmt(n) { return String(TMPL).replace('{c}', n).replace('{n}', total); }

    function persistStep() {
        try { sessionStorage.setItem(KEY + '.step', String(current)); } catch (e) {}
    }

    function show(n) {
        n = Math.min(Math.max(1, n), total);
        current = n;
        stepEls.forEach(function (el, i) { el.style.display = (i + 1 === n) ? '' : 'none'; });
        labelEl.textContent = fmt(n);
        backBtn.style.display = (n === 1) ? 'none' : '';
        nextBtn.style.display = (n === total) ? 'none' : '';
        regBtn.style.display = (n === total) ? '' : 'none';
        persistStep();
        window.scrollTo({ top: form.getBoundingClientRect().top + window.scrollY - 60, behavior: 'smooth' });
    }

    function save() {
        try {
            const d = {};
            form.querySelectorAll('input[name],select[name],textarea[name]').forEach(function (el) {
                if (el.type === 'file') return;
                d[el.name] = (el.type === 'checkbox') ? (el.checked ? 'on' : '') : el.value;
            });
            sessionStorage.setItem(KEY, JSON.stringify(d));
        } catch (e) {}
    }

    let current = 1;
    try {
        const s = sessionStorage.getItem(KEY + '.step');
        if (s) current = parseInt(s, 10) || 1;
        const raw = sessionStorage.getItem(KEY);
        if (raw) {
            const d = JSON.parse(raw);
            const skipHs = new URLSearchParams(location.search).has('selected');
            Object.keys(d).forEach(function (name) {
                if (name === 'healthsite_id' && skipHs) return;
                const el = form.elements[name];
                if (!el || el.type === 'file') return;
                try {
                    if (el.type === 'checkbox') el.checked = d[name] === 'on';
                    else el.value = d[name];
                } catch (e2) {}
            });
        }
    } catch (e) {}

    // A healthsite search/import reloads the page (full navigation) after the
    // user may already have picked a photo on step 2. Browsers clear file
    // inputs on reload, so restore the compressed photo cached in sessionStorage.
    try {
        const rawPhoto = sessionStorage.getItem(KEY + '.photo');
        if (rawPhoto) {
            const p = JSON.parse(rawPhoto);
            const input = document.getElementById('photo-file');
            if (p && p.data && input) {
                fetch(p.data).then(function (r) { return r.blob(); }).then(function (blob) {
                    try {
                        const dt = new DataTransfer();
                        dt.items.add(new File([blob], p.name || 'device_photo.jpg',
                                              { type: blob.type || 'image/jpeg' }));
                        input.files = dt.files;
                        const img = document.getElementById('photo-preview');
                        if (img) { img.src = p.data; img.style.display = 'inline-block'; }
                    } catch (e2) {}
                }).catch(function () {});
            }
        }
    } catch (e) {}

    show(current);
    form.addEventListener('input', save);
    form.addEventListener('change', save);
    form.addEventListener('submit', function () {
        try { sessionStorage.removeItem(KEY + '.photo'); } catch (e) {}
    });
    window.fmmSavePhoto = function (blob, name) {
        try {
            const reader = new FileReader();
            reader.onload = function () {
                try {
                    sessionStorage.setItem(KEY + '.photo',
                        JSON.stringify({ name: name, data: reader.result }));
                } catch (e) {}
            };
            reader.readAsDataURL(blob);
        } catch (e) {}
    };
    window.wStep = function (delta) {
        show(current + delta);
    };
})();
"""
    return (js.replace("@@STEP_KEY@@", json.dumps(f"fmm_new_{device_id}"))
             .replace("@@STEP_TMPL@@", json.dumps(step_tmpl)))


def _device_form(lang, device_id: str, orgs, selected: str = ""):
    _ = make_t(lang)

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

    org_options = [Option(o["name"], value=o["id"]) for o in orgs]
    hs_options = [Option(_("new_device.select_healthsite"), value="")]
    for o in orgs:
        hs_options.append(Option(o["name"], value=o["id"], selected=(o["id"] == selected)))

    step_back = _("new_device.wizard_back")
    step_next = _("new_device.wizard_next")
    step_script = _wizard_script(device_id, _("new_device.wizard_step"))

    return Form(
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
            cls="card", style="margin-bottom:14px;", data_step="1"
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
                        fmmCompressImage(new File([blob], 'camera_photo.jpg', { type: 'image/jpeg' }), 1024, 0.8)
                            .then(function (cb) {
                                fmmSetFiles(document.getElementById('photo-file'), cb, 'camera_photo.jpg');
                                if (window.fmmSavePhoto) window.fmmSavePhoto(cb, 'camera_photo.jpg');
                                const img = document.getElementById('photo-preview');
                                img.src = URL.createObjectURL(cb);
                                img.style.display = 'inline-block';
                                stopCamera();
                            }).catch(function () { stopCamera(); });
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
                        fmmCompressImage(input.files[0], 1024, 0.8).then(function (blob) {
                            const name = input.files[0].name.replace(/\\.[^.]+$/, '') + '.jpg';
                            fmmSetFiles(input, blob, name);
                            if (window.fmmSavePhoto) window.fmmSavePhoto(blob, name);
                        }).catch(function () {});
                    }
                }
                """),
                cls="form-group",
            ),
            cls="card", style="margin-bottom:14px;", data_step="2"
        ),
        Div(
            H3(_("new_device.location"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(
                    Button(
                        "📍 " + _("new_device.capture_location"),
                        type="button", cls="btn btn-secondary btn-sm",
                        onclick="captureLoc()",
                        style="align-self:flex-start;white-space:nowrap;flex-centre:0;"
                    ),
                ),
                Div(
                    Div(Label(_("new_device.latitude"), cls="label", for_="loc-lat"),
                        Input(id="loc-lat", name="latitude", cls="input",
                              placeholder=_("new_device.latitude_placeholder")),
                        cls="form-group"),
                    Div(Label(_("new_device.longitude"), cls="label", for_="loc-lng"),
                        Input(id="loc-lng", name="longitude", cls="input",
                              placeholder=_("new_device.longitude_placeholder")),
                        cls="form-group"),
                    # style="display:flex;gap:14px;align-items:flex-centre;"
                    cls="form-row",
                ),
                Script("""
                function captureLoc() {
                    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
                    navigator.geolocation.getCurrentPosition((pos) => {
                        document.getElementById('loc-lat').value = pos.coords.latitude;
                        document.getElementById('loc-lng').value = pos.coords.longitude;
                        const f = document.getElementById('device-form');
                        if (f) f.dispatchEvent(new Event('input', { bubbles: true }));
                    }, (err) => alert('Geolocation error: ' + err.message));
                }
                """),
                cls="form-group",
            ),
            Div(
                Div(
                    Div(Label(_("new_device.healthsite_label"), cls="label", for_="healthsite_id"),
                        Select(*hs_options, id="healthsite_id", name="healthsite_id", cls="input"),
                        Button("🔍 " + _("new_device.search_healthsite_btn"), type="button",
                                                        cls="btn btn-secondary btn-sm",
                                                        onclick="document.getElementById('hsDialog').showModal()",
                                                        style="white-space:nowrap;flex-shrink:0;gap:10px;margin-top:8px;"),
                        cls="form-group"),
                    Div(Label(_("new_device.location_label"), cls="label"),
                        Input(name="location", cls="input", placeholder=_("new_device.location_placeholder")),
                        cls="form-group"),
                    cls="form-row"
                ),
                cls="form-group"
            ),
            Div(
                Div(Label(_("new_device.org_label"), cls="label", for_="organization_id"),
                    Select(*org_options, id="organization_id", name="organization_id", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            cls="card", style="margin-bottom:14px;", data_step="3"
        ),
        Div(
            H3(_("new_device.acquisition_optional"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label(_("new_device.acquisition_label"), cls="label"),
                    Select(Option(_("new_device.acquisition_purchased"), value="purchased"),
                        Option(_("new_device.acquisition_donated"), value="donated"),
                        Option(_("new_device.acquisition_leased"), value="leased"),
                        name="acquisition_type", cls="input"),
                    cls="form-group"),
                Div(Label(_("new_device.acquisition_date"), cls="label"),
                    Input(name="acquisition_date", type="date", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label(_("new_device.status_label"), cls="label"),
                    Select(Option(_("new_device.status_operational"), value="operational"),
                        Option(_("new_device.status_fault"), value="fault"),
                        Option(_("new_device.status_decommissioned"), value="decommissioned"),
                        Option(_("new_device.status_maintenance"), value="maintenance"),
                        name="status", cls="input"),
                    cls="form-group"),
            ),
            Div(
                Div(Label(_("new_device.last_maintenance"), cls="label"),
                    Input(name="last_maintenance", type="date", cls="input"),
                    cls="form-group"),
                Div(Label(_("new_device.next_maintenance"), cls="label"),
                    Input(name="next_maintenance", type="date", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            cls="card", style="margin-bottom:14px;", data_step="4"
        ),
        Div(
            H3(_("new_device.notes"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(Textarea(name="notes", cls="input", placeholder=_("new_device.notes_placeholder"), rows="3"),
                cls="form-group"),
            cls="card", style="margin-bottom:14px;", data_step="5"
        ),
        Div(
            Button(step_back, id="step-back", type="button", cls="btn btn-secondary",
                   onclick="wStep(-1)", style="display:none;"),
            Div(
                A(_("new_device.cancel"), href="/devices", cls="btn btn-secondary"),
                Span(id="step-label", style="font-size:0.875rem;color:var(--c-text-3);font-weight:600;"),
                Button(step_next, id="step-next", type="button", cls="btn btn-primary",
                       onclick="wStep(1)"),
                Button(_("new_device.register"), id="step-register", type="submit", cls="btn btn-primary",
                       style="display:none;"),
                style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;"
            ),
            style="display:flex;justify-content:space-between;align-items:center;gap:10px;"
        ),
        Script(step_script),
        id="device-form",
        method="post", action=f"/device/{device_id}/new",
        enctype="multipart/form-data",
        style="max-width:720px;"
    )


def _build_page(req, lang, device_id, form, orgs, *, results=None, search=None, error="",
                open_hs=False, selected=""):
    _ = make_t(lang)

    flash = ""
    f = req.query_params.get("flash")
    ok = req.query_params.get("ok")
    if f:
        flash = Div(f, style="color:{};font-size:0.875rem;margin-bottom:14px;".format(
            "var(--c-green)" if ok == "1" else "var(--c-danger)"))

    scripts = [Script(GEOLOC_JS)]
    if open_hs:
        scripts.append(Script("document.getElementById('hsDialog') && document.getElementById('hsDialog').showModal();"))

    content = Div(
        flash,
        Div(form),
        _hs_dialog(_, results=results, search=search, error=error,
                   search_url=f"/device/{device_id}/new/search-healthsites",
                   import_url=f"/device/{device_id}/new/import-healthsite",
                   dialog_id="hsDialog"),
        *scripts,
    )
    return page_shell(content, current=f"/device/{device_id}/new", title=_("title.add_device"), lang=lang)


@rt("/device/{device_id}/new/search-healthsites")
async def post(req, device_id: str, lat: str = "", lng: str = "", radius_km: str = "2"):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        lat_f = float(lat or 0)
        lng_f = float(lng or 0)
        radius_f = min(max(float(radius_km or 0), 0.1), 2.0)
    except ValueError:
        return RedirectResponse(f"/device/{device_id}/new", status_code=302)

    if not lat_f or not lng_f:
        return RedirectResponse(f"/device/{device_id}/new", status_code=302)

    try:
        orgs = await org_api.get_my_organizations(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        orgs = []
    except Exception:
        orgs = []

    form = _device_form(lang, device_id, orgs)
    search = (lat_f, lng_f, radius_f)
    try:
        data = await org_api.search_healthsites(token, {
            "lat": lat_f, "lng": lng_f, "radius_km": radius_f,
        })
        return _build_page(req, lang, device_id, form, orgs,
                           results=data.get("facilities", []),
                           search=search, open_hs=True)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            err = _("groups.import_nokey")
        else:
            err = _("groups.import_fail")
    except Exception:
        err = _("groups.import_fail")
    return _build_page(req, lang, device_id, form, orgs, search=search, error=err, open_hs=True)


@rt("/device/{device_id}/new/import-healthsite")
async def post(req, device_id: str, osm_id: str = "", osm_type: str = "", name: str = "",
               country: str = "", region: str = "", address: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    facility = {
        "osm_id": osm_id.strip(),
        "osm_type": osm_type.strip(),
        "name": name.strip(),
        "country": country.strip(),
    }
    if region.strip():
        facility["region"] = region.strip()
    if address.strip():
        facility["address"] = address.strip()

    if not facility["osm_id"] or not facility["name"]:
        return RedirectResponse(f"/device/{device_id}/new", status_code=302)

    try:
        result = await org_api.import_healthsite(token, facility, role="technician")
        if result.get("added"):
            selected = result.get("id", "")
            return RedirectResponse(
                f"/device/{device_id}/new?selected={selected}&flash={quote(_('groups.import_added'))}&ok=1",
                status_code=302)
        return RedirectResponse(f"/device/{device_id}/new?flash={quote(_('groups.import_dup'))}", status_code=302)
    except Exception:
        pass
    return RedirectResponse(f"/device/{device_id}/new?flash={quote(_('groups.import_fail'))}", status_code=302)


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
    if field("healthsite_id"):   payload["healthsite_id"]    = field("healthsite_id")
    if field("manufacturer"):    payload["manufacturer"]     = field("manufacturer")
    if field("model"):           payload["model"]            = field("model")
    if field("serial_number"):   payload["serial_number"]    = field("serial_number")
    if field("category_id"):     payload["category_id"]      = field("category_id")
    if field("location"):        payload["location"]         = field("location")
    if field("acquisition_type"):payload["acquisition_type"] = field("acquisition_type")
    if field("acquisition_date"):payload["acquisition_date"] = field("acquisition_date")
    if field("last_maintenance"):payload["last_maintenance"] = field("last_maintenance")
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
