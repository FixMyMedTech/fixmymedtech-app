from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
import os, json, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.devices.api as devices_api

from components import page_shell, status_badge, fmt_date, map_component
from features.devices.static.guides import category_label
from i18n import t as make_t
rt = APIRouter()


def _org_loc(org: dict) -> str:
    bits = []
    if org.get("country"):
        bits.append(str(org["country"]))
    if org.get("region"):
        bits.append(str(org["region"]))
    if org.get("address"):
        bits.append(str(org["address"]))
    return " · ".join(bits)

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


@rt("/device/{device_id}/photo")
async def get_photo(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    try:
        content, ctype = await devices_api.get_device_photo(token, device_id)
        return Response(content=content, media_type=ctype)
    except Exception:
        return Response(status_code=404)


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
    hs = d.get("healthsite") or {}
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
                style="min-width:0;flex:1;",
            ),
            Button("▣ " + _("device_detail.show_qr"), type="button",
                   cls="btn btn-primary btn-sm", onclick="showDeviceQR()",
                   style="flex-shrink:0;"),
            style="display:flex;align-items:center;gap:12px;background:var(--c-primary-lt);border:1px solid #a7d9ce;border-radius:var(--r-md);padding:12px 16px;margin-bottom:20px;"
        ),
        # QR popup + generator
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/qrious/4.0.2/qrious.min.js"),
        Script(f"""
        var _deviceQr = null;
        var _deviceQrUrl = {json.dumps(qr_url)};
        var _deviceId = {json.dumps(device_id)};
        var _deviceLogo = new Image();
        var _deviceLogoReady = false;
        _deviceLogo.onload = function () {{ _deviceLogoReady = true; if (_deviceQr) composeDeviceQR(); }};
        _deviceLogo.onerror = function () {{ _deviceLogoReady = false; }};
        _deviceLogo.src = '/static/fixmymedtech_logo.png';

        function _fmmRoundRect(ctx, x, y, w, h, r) {{
            if (ctx.roundRect) {{ ctx.beginPath(); ctx.roundRect(x, y, w, h, r); return; }}
            ctx.beginPath();
            ctx.moveTo(x + r, y);
            ctx.arcTo(x + w, y, x + w, y + h, r);
            ctx.arcTo(x + w, y + h, x, y + h, r);
            ctx.arcTo(x, y + h, x, y, r);
            ctx.arcTo(x, y, x + w, y, r);
            ctx.closePath();
        }}

        function _qrContentBox(qcanvas) {{
            var w = qcanvas.width, h = qcanvas.height;
            var data = qcanvas.getContext('2d').getImageData(0, 0, w, h).data;
            var minx = w, miny = h, maxx = -1, maxy = -1;
            for (var y = 0; y < h; y++) {{
                for (var x = 0; x < w; x++) {{
                    var i = (y * w + x) * 4;
                    if (data[i] < 128 && data[i + 1] < 128 && data[i + 2] < 128) {{
                        if (x < minx) minx = x;
                        if (y < miny) miny = y;
                        if (x > maxx) maxx = x;
                        if (y > maxy) maxy = y;
                    }}
                }}
            }}
            if (maxx < minx) return {{ x: 0, y: 0, w: w, h: h }};
            return {{ x: minx, y: miny, w: maxx - minx + 1, h: maxy - miny + 1 }};
        }}

        function composeDeviceQR() {{
            if (!window.QRious) return null;
            if (!_deviceQr) {{
                _deviceQr = new QRious({{
                    value: _deviceQrUrl,
                    size: 280,
                    level: 'H',
                    padding: 0,
                    background: '#ffffff',
                    foreground: '#000000'
                }});
            }}
            var QR = 280, MARGIN = 28, FOOTER = 62;
            var W = QR + MARGIN * 2;
            var H = QR + MARGIN * 2 + FOOTER;
            var canvas = document.getElementById('device-qr-canvas');
            canvas.width = W; canvas.height = H;
            var ctx = canvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, W, H);
            // QRious left/top-aligns the modules (integer cell size), so crop the
            // real QR content and draw it centered to fill the square exactly.
            var cb = _qrContentBox(_deviceQr.canvas);
            ctx.drawImage(_deviceQr.canvas, cb.x, cb.y, cb.w, cb.h, MARGIN, MARGIN, QR, QR);
            if (_deviceLogoReady) {{
                var maxL = Math.round(QR * 0.24);
                var ar = (_deviceLogo.naturalWidth || 1) / (_deviceLogo.naturalHeight || 1);
                var lw, lh;
                if (ar >= 1) {{ lw = maxL; lh = Math.round(maxL / ar); }}
                else {{ lh = maxL; lw = Math.round(maxL * ar); }}
                var ccx = MARGIN + QR / 2, ccy = MARGIN + QR / 2;
                var pad = 8;
                ctx.fillStyle = '#ffffff';
                _fmmRoundRect(ctx, ccx - lw / 2 - pad, ccy - lh / 2 - pad, lw + pad * 2, lh + pad * 2, 8);
                ctx.fill();
                ctx.drawImage(_deviceLogo, ccx - lw / 2, ccy - lh / 2, lw, lh);
            }}
            ctx.textAlign = 'center';
            ctx.fillStyle = '#111111';
            ctx.font = 'bold 20px Arial, Helvetica, sans-serif';
            ctx.fillText('FixMyMedTech QR', W / 2, MARGIN + QR + 30);
            ctx.fillStyle = '#666666';
            ctx.font = '13px "Courier New", monospace';
            ctx.fillText(_deviceId, W / 2, MARGIN + QR + 50);
            return canvas;
        }}

        function showDeviceQR() {{
            if (!window.QRious) {{ alert('QR library unavailable'); return; }}
            composeDeviceQR();
            document.getElementById('deviceQrDialog').showModal();
        }}

        function downloadDeviceQR() {{
            var canvas = composeDeviceQR();
            if (!canvas) return;
            var a = document.createElement('a');
            a.href = canvas.toDataURL('image/png');
            a.download = 'device-qr-' + _deviceId + '.png';
            document.body.appendChild(a); a.click(); a.remove();
        }}

        function printDeviceQR() {{
            var canvas = composeDeviceQR();
            if (!canvas) return;
            var w = window.open('', '_blank');
            if (!w) return;
            w.document.write('<html><head><title>' + document.title + '</title></head>'
                + '<body style="margin:0;display:flex;align-items:center;justify-content:center;height:100vh;">'
                + '<img src="' + canvas.toDataURL('image/png') + '" style="width:360px;height:auto;" '
                + 'onload="window.focus();window.print();"></body></html>');
            w.document.close();
        }}
        """),
        Dialog(
            Div(
                H3(_("device_detail.qr_title"), style="margin:0 0 4px 0;font-size:1.05rem;"),
                P(_("device_detail.qr_hint"), style="color:var(--c-text-3);font-size:0.8rem;margin:0 0 10px 0;"),
                Div(
                    Canvas(id="device-qr-canvas", style="max-width:100%;height:auto;border-radius:8px;"),
                    style="display:flex;justify-content:center;margin-bottom:14px;"
                ),
                Div(
                    Button("⬇ " + _("device_detail.download_qr"), type="button",
                           cls="btn btn-primary btn-sm", onclick="downloadDeviceQR()"),
                    Button("🖨 " + _("device_detail.print_qr"), type="button",
                           cls="btn btn-secondary btn-sm", onclick="printDeviceQR()"),
                    Button(_("groups.close_btn"), type="button", cls="btn btn-secondary btn-sm",
                           onclick="document.getElementById('deviceQrDialog').close()"),
                    style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;"
                ),
                style="padding:18px;max-width:360px;text-align:center;"
            ),
            id="deviceQrDialog",
            style="border:none;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);"
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
                        (_("device_detail.status"),   d.get("status",_("common.fallback"))),
                        (_("device_detail.acquisition"),   f"{d.get('acquisition_type',_('common.fallback'))} · {fmt_date(d.get('acquisition_date',''))}"),
                        (_("device_detail.last_maint"), fmt_date(d.get("last_maintenance",""))),
                        (_("device_detail.next_maint"), fmt_date(d.get("next_maintenance",""))),
                    ]]
                ),
                cls="card"
            ),
            cls="two-col", style="margin-bottom:16px;"
        ),
        Div(
            # Photo
            Div(
                Img(src=f"/device/{device_id}/photo?v={d.get('photo_processed_key') or 'original'}", alt=d.get("name", ""),
                    style="width:100%;max-height:360px;object-fit:cover;border-radius:var(--r-md);"),
                cls="card", style="padding:6px;margin-bottom:16px;",
            ) if d.get("photo_key") else "",
            # Map
            Div(
                H3(_("device_detail.location_map"), style="margin-bottom:12px;"),
                Div(
                    P(d.get("location",_("common.fallback")), style="font-size:0.85rem;margin:2px 0 0;"),
                    Div(hs.get("name", ""), style="font-weight:600;font-size:0.9rem;"),
                    P(_org_loc(hs), style="color:var(--c-text-3);font-size:0.85rem;margin:2px 0 0;")
                    if _org_loc(hs) else "",
                    # style="background:var(--c-bg-soft,#f4f4f4);border-radius:8px;padding:10px 12px;margin-bottom:12px;"
                ) if hs.get("name") else "",
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
            cls="two-col", style="margin-bottom:16px;"
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

