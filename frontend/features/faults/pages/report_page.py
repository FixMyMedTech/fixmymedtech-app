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
from components import page_shell, status_badge, fmt_date
import features.auth.api as auth_api
from i18n import t as make_t
rt = APIRouter()

def _severity_text(text: str) -> str:
    if " — " in text:
        level, desc = text.split(" — ", 1)
        return f"{desc} - {level}"
    return text

# ══════════════════════════════════════════════════════════════
# FAULT REPORT
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/report")
async def get(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/report", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
        full_name = me.get("full_name") or req.session.get("user_email", "")
    except Exception:
        full_name = req.session.get("user_email", "")

    assignees = []
    try:
        assignees = await faults_api.get_fault_assignees(token, device_id)
    except Exception:
        assignees = []

    assignee_field = ""
    if assignees:
        assignee_options = [Option(_("report_fault.assignee_none"), value="")]
        for a in assignees:
            role_label = _("role." + (a.get("role") or "technician"))
            assignee_options.append(
                Option(f"{a.get('full_name','')} — {role_label}", value=a["id"])
            )
        assignee_field = Div(
            Label(_("report_fault.assignee_label"), cls="label"),
            Select(
                *assignee_options,
                name="assigned_to",
                cls="input",
            ),
            cls="form-group",
            style="margin-top:12px;"
        )

    content = Div(
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}",
              style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:block;margin-bottom:16px;"),
            H2(_("report_fault.heading"), style="margin-bottom:6px;"),
            P(_("report_fault.desc"),
              style="margin-bottom:16px;"),
            Div(
                Label(_("report_fault.description_label"), cls="label"),
                Textarea(name="description", cls="input", rows="4",
                         placeholder=_("report_fault.description_placeholder")),
                cls="form-group"
            ),
            Div(
                Label(_("report_fault.severity_label"), cls="label"),
                Div(
                    *[Label(Input(type="radio", name="severity", value=v,
                                  checked=(v=="medium")),
                             f" {_severity_text(_(f'report_fault.severity_{v}'))}",
                             style="display:block;padding:8px 10px;margin-bottom:6px;font-size:0.875rem;cursor:pointer;")
                      for v in ["low", "medium", "high", "critical"]],
                )
            ),
            Div(
                Label(_("report_fault.name_label"), cls="label"),
                Div(full_name, cls="input",
                    style="opacity:.7;"),
                cls="form-group", style="margin-top:12px;"
            ),
            assignee_field,
            Div(
                H3(_("report_fault.photo"), style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
                P(_("report_fault.photo_desc"), style="font-size:0.85rem;color:var(--c-text-3);margin-bottom:14px;"),
                Div(
                    Div(
                        Button(_("report_fault.photo_take_label"), type="button", id="fault-open-camera",
                               cls="btn btn-secondary", onclick="faultOpenCamera()"),
                        Button(_("report_fault.photo_capture_label"), type="button", id="fault-capture-photo",
                               cls="btn btn-primary", style="display:none;", onclick="faultCapturePhoto()"),
                        Button(_("report_fault.photo_close_label"), type="button", id="fault-close-camera",
                               cls="btn btn-secondary", style="display:none;", onclick="faultStopCamera()"),
                        style="display:flex;gap:10px;margin-bottom:10px;"
                    ),
                    Video(id="fault-camera-view", autoplay=True, playsinline=True, muted=True,
                          style="display:none;width:100%;max-height:280px;border-radius:8px;margin-bottom:10px;background:#000;"),
                    Div(
                        Div(Label(_("report_fault.photo_choose_label"), cls="label", for_="fault-photo-file"),
                            Input(type="file", id="fault-photo-file", name="photo",
                                  accept="image/*", cls="input",
                                  onchange="faultPreviewPhoto(this)"),
                            cls="form-group"),
                    ),
                    Div(
                        Img(id="fault-photo-preview", alt="", style="display:none;max-width:100%;max-height:220px;border-radius:8px;margin-top:10px;"),
                        style="text-align:center;"
                    ),
                    Script("""
                    let faultCameraStream = null;

                    function faultOpenCamera() {
                        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                            alert('Camera not supported in this browser');
                            return;
                        }
                        navigator.mediaDevices.getUserMedia({
                            video: { facingMode: { ideal: 'environment' } },
                            audio: false
                        }).then((stream) => {
                            faultCameraStream = stream;
                            const video = document.getElementById('fault-camera-view');
                            video.srcObject = stream;
                            video.style.display = 'block';
                            video.play();
                            document.getElementById('fault-open-camera').style.display = 'none';
                            document.getElementById('fault-capture-photo').style.display = 'inline-block';
                            document.getElementById('fault-close-camera').style.display = 'inline-block';
                        }).catch((err) => alert('Camera error: ' + err.message));
                    }

                    function faultStopCamera() {
                        if (faultCameraStream) {
                            faultCameraStream.getTracks().forEach(function (t) { t.stop(); });
                            faultCameraStream = null;
                        }
                        const video = document.getElementById('fault-camera-view');
                        video.srcObject = null;
                        video.style.display = 'none';
                        document.getElementById('fault-open-camera').style.display = 'inline-block';
                        document.getElementById('fault-capture-photo').style.display = 'none';
                        document.getElementById('fault-close-camera').style.display = 'none';
                    }

                    function faultCapturePhoto() {
                        const video = document.getElementById('fault-camera-view');
                        const canvas = document.createElement('canvas');
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        canvas.getContext('2d').drawImage(video, 0, 0);
                        canvas.toBlob(function (blob) {
                            if (!blob) return;
                            const file = new File([blob], 'camera_photo.jpg', { type: blob.type || 'image/jpeg' });
                            const dt = new DataTransfer();
                            dt.items.add(file);
                            document.getElementById('fault-photo-file').files = dt.files;
                            const img = document.getElementById('fault-photo-preview');
                            img.src = URL.createObjectURL(blob);
                            img.style.display = 'inline-block';
                            faultStopCamera();
                        }, 'image/jpeg', 0.92);
                    }

                    function faultPreviewPhoto(input) {
                        if (input.files && input.files[0]) {
                            const img = document.getElementById('fault-photo-preview');
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
            Button(_("report_fault.submit"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:8px;"),
            style="padding:16px;"
        ),
        cls="card", style="max-width:560px;margin:24px auto;"
    )

    return page_shell(
        Form(content, method="post", action=f"/d/{device_id}/report",
             enctype="multipart/form-data"),
        current="/devices", title=_("title.report_fault"), lang=lang
    )


@rt("/d/{device_id}/report")
async def post(req, device_id: str, description: str,
               severity: str = "medium", assigned_to: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/report", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    if not description.strip():
        return RedirectResponse(f"/d/{device_id}/report", status_code=302)

    try:
        me = await auth_api.get_me(token)
        full_name = me.get("full_name") or req.session.get("user_email", "Anonymous")
    except Exception:
        full_name = req.session.get("user_email", "Anonymous")

    data = {
        "device_id": device_id,
        "description": description,
        "severity": severity,
        "reporter_name": full_name,
    }
    if assigned_to:
        data["assigned_to"] = assigned_to

    fault_id = None
    try:
        result = await faults_api.submit_fault_public(data)
        fault_id = (result or {}).get("id")
    except Exception:
        pass

    if fault_id:
        try:
            form = await req.form()
            photo = form.get("photo")
            if photo is not None and getattr(photo, "filename", ""):
                photo_data = await photo.read()
                if photo_data:
                    await faults_api.upload_fault_photo(
                        token, str(fault_id),
                        photo.filename or "fault_photo.jpg",
                        photo_data, photo.content_type,
                    )
        except Exception:
            pass

    return page_shell(
        Div(
            Div(
                Div("✓", style="width:52px;height:52px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.3rem;display:flex;align-items:center;justify-content:center;margin:0 auto 14px;"),
                H2(_("report_fault.success_heading")),
                P(_("report_fault.success_msg")),
                A(_("report_fault.success_back"), href=f"/d/{device_id}",
                  cls="btn btn-secondary", style="margin-top:16px;"),
                style="text-align:center;padding:40px 24px;"
            ),
            cls="card", style="max-width:560px;margin:80px auto;"
        ),
        current="/devices", lang=lang
    )
