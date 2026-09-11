from fasthtml.common import *
from starlette.responses import RedirectResponse, Response

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.faults.api as faults_api

from components import *
from components import page_shell, status_badge, fmt_date, pub_shell, assignee_options
from i18n import t as make_t

rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# PUBLIC FAULT DETAIL
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/fault/{fault_id}", methods=["get"])
async def get_fault_public(req, device_id: str, fault_id: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        fault = await faults_api.get_fault_public(fault_id)
    except Exception:
        return pub_shell(
            Div(
                Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                H2(_("public_qr.not_found")),
                P(_("public_qr.not_found_msg")),
                A(_("public_qr.back"), href=f"/d/{device_id}", cls="btn btn-primary",
                  style="margin-top:20px;"),
                style="text-align:center;padding:60px 24px;"
            ),
            lang=lang
        )

    device = fault.get("device") or {}
    assigned = fault.get("assigned_to_profile") or {}
    reported_by = fault.get("reported_by_profile") or {}

    sec_head = lambda t: H3(t,
        style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;")

    rows = [
        (_("fault_detail.status"),      status_badge(fault.get("status", "open"), "fault", lang=lang)),
        (_("fault_detail.severity"),    status_badge(fault.get("severity", "medium"), "severity", lang=lang)),
        (_("fault_detail.reported_at"), fmt_date(fault.get("reported_at", ""))),
        (_("fault_detail.reported_by"), reported_by.get("full_name") or fault.get("reporter_name", _("common.fallback"))),
        (_("fault_detail.assigned_to"), assigned.get("full_name", _("common.fallback"))),
        (_("fault_detail.resolved_at"), fmt_date(fault.get("resolved_at", ""))),
    ]

    # Botón editar solo si hay sesión con rol técnico/admin
    edit_btn = ""
    token = auth_helper.get_token(req)
    if token:
        try:
            me = await auth_api.get_me(token)
        except Exception:
            me = {}
        if auth_helper.user_can_edit(me, device.get("organization_id")):
            edit_btn = Div(
                A(_("fault_detail.edit"), href=f"/d/{device_id}/fault/{fault['id']}/edit",
                  cls="btn btn-primary", style="width:100%;justify-content:center;"),
                cls="pub-section"
            )

    content = Div(
        # Title
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}",
              style="font-size:0.8rem;color:var(--c-text-3);text-decoration:none;margin-bottom:10px;display:inline-block;"),
            Div(f"{device.get('name','')}",
                style="font-size:0.78rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;"),
            H1(_("fault_detail.heading"), style="font-family:var(--font-display);font-size:1.25rem;margin:2px 0 0;"),
            cls="pub-section"
        ),
        # Details
        Div(
            sec_head(_("fault_detail.info")),
            Dl(
                *[Div(Dt(k), Dd(v), cls="info-row") for k, v in rows],
                cls="info-list", style="padding:0;"
            ),
            cls="pub-section"
        ),
        # Description
        Div(
            sec_head(_("fault_detail.description")),
            P(fault.get("description", ""), style="font-size:0.9rem;white-space:pre-wrap;"),
            cls="pub-section"
        ),
        # Photo
        Div(
            sec_head(_("fault_detail.photo")),
            Img(src=f"/d/{device_id}/fault/{fault.get('id')}/photo",
                alt=_("fault_detail.photo"),
                style="width:100%;border-radius:8px;"),
            cls="pub-section"
        ) if fault.get("photo_key") else "",
        # Resolution
        Div(
            sec_head(_("fault_detail.resolution")),
            P(fault.get("resolution_notes", _("fault_detail.no_resolution")),
              style="font-size:0.9rem;white-space:pre-wrap;color:var(--c-text-2);"),
            cls="pub-section"
        ) if fault.get("resolution_notes") else "",
        edit_btn,
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{_('fault_detail.heading')} — {_('brand')}", lang=lang)


@rt("/d/{device_id}/fault/{fault_id}/photo")
async def get_fault_photo_public(device_id: str, fault_id: str):
    try:
        content, ctype = await faults_api.get_fault_photo_public(fault_id)
        return Response(content=content, media_type=ctype)
    except Exception:
        return Response(status_code=404)


# ══════════════════════════════════════════════════════════════
# PUBLIC FAULT EDIT
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/fault/{fault_id}/edit", methods=["get"])
async def get_fault_edit(req, device_id: str, fault_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/fault/{fault_id}/edit", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}
    fault_obj = await faults_api.get_fault_public(fault_id)
    fault_device = (fault_obj.get("device") or {}) if isinstance(fault_obj, dict) else {}
    if not auth_helper.user_can_edit(me, fault_device.get("organization_id")):
        return RedirectResponse(f"/d/{device_id}/fault/{fault_id}", status_code=302)

    try:
        fault = await faults_api.get_fault_public(fault_id)
    except Exception:
        return RedirectResponse(f"/d/{device_id}", status_code=302)

    device = fault.get("device") or {}
    assignees = []
    try:
        assignees = await faults_api.get_fault_assignees(token, device_id)
    except Exception:
        assignees = []

    content = Div(
        # Title
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}/fault/{fault_id}",
              style="font-size:0.8rem;color:var(--c-text-3);text-decoration:none;margin-bottom:10px;display:inline-block;"),
            Div(f"{device.get('name','')}",
                style="font-size:0.78rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;"),
            H1(_("fault_detail.edit"), style="font-family:var(--font-display);font-size:1.25rem;margin:2px 0 0;"),
            cls="pub-section"
        ),
        _fault_edit_form(fault, device_id, assignees, lang),
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return page_shell(content, title=f"{_('fault_detail.edit')} — {_('brand')}", lang=lang)


@rt("/d/{device_id}/fault/{fault_id}/edit", methods=["post"])
async def post_fault_edit(req, device_id: str, fault_id: str, status: str = "",
                          severity: str = "", assigned_to: str = "",
                          description: str = "", resolution_notes: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/fault/{fault_id}/edit", status_code=302)

    data = {}
    if status:
        data["status"] = status
    if severity:
        data["severity"] = severity
    if assigned_to:
        data["assigned_to"] = assigned_to
    data["description"] = description
    data["resolution_notes"] = resolution_notes
    try:
        await faults_api.update_fault(token, fault_id, data)
    except Exception:
        pass

    try:
        form = await req.form()
        photo = form.get("photo")
        if photo is not None and getattr(photo, "filename", ""):
            photo_data = await photo.read()
            if photo_data:
                await faults_api.upload_fault_photo(
                    token, fault_id,
                    photo.filename or "fault_photo.jpg",
                    photo_data, photo.content_type,
                )
    except Exception:
        pass

    return RedirectResponse(f"/d/{device_id}/fault/{fault_id}", status_code=303)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _fault_edit_form(fault, device_id, assignees, lang):
    _ = make_t(lang)
    sec_head = lambda t: H3(t,
        style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;")
    return Form(
        Div(
            sec_head(_("fault_detail.edit")),
            Div(
                Label(_("fault_detail.status"), cls="label"),
                Select(*[Option(_(f"badge.{v}"), value=v,
                                selected=(fault.get("status") == v))
                         for v in ["open", "assigned", "in_progress", "resolved"]],
                       name="status", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("fault_detail.severity"), cls="label"),
                Select(*[Option(_(f"badge.{v}"), value=v,
                                selected=(fault.get("severity") == v))
                         for v in ["low", "medium", "high", "critical"]],
                       name="severity", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("fault_detail.assigned_to"), cls="label"),
                Select(*assignee_options(assignees, fault.get("assigned_to") or "", lang),
                       name="assigned_to", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("fault_detail.description"), cls="label"),
                Textarea(fault.get("description", ""), name="description", rows="3",
                         cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("fault_detail.resolution"), cls="label"),
                Textarea(fault.get("resolution_notes", ""), name="resolution_notes", rows="3",
                         cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                sec_head(_("fault_detail.photo")),
                Img(src=f"/d/{device_id}/fault/{fault['id']}/photo?v={fault.get('photo_key') or 'x'}",
                    id="fault-edit-photo-preview",
                    alt=_("fault_detail.photo"),
                    style="width:100%;border-radius:8px;margin-bottom:10px;"),
                Label(_("fault_detail.change_photo"), cls="label", for_="fault-edit-photo"),
                Input(type="file", id="fault-edit-photo", name="photo", accept="image/*",
                      cls="input", onchange="faultEditPreviewPhoto(this)"),
                cls="form-group", style="margin-top:10px;"
            ) if fault.get("photo_key") else Div(
                sec_head(_("fault_detail.photo")),
                Label(_("fault_detail.change_photo"), cls="label", for_="fault-edit-photo"),
                Input(type="file", id="fault-edit-photo", name="photo", accept="image/*",
                      cls="input", onchange="faultEditPreviewPhoto(this)"),
                cls="form-group", style="margin-top:10px;"
            ),
            Script("""
            function faultEditPreviewPhoto(input) {
                if (input.files && input.files[0]) {
                    const preview = document.getElementById('fault-edit-photo-preview');
                    const reader = new FileReader();
                    reader.onload = function (e) {
                        if (preview) preview.src = e.target.result;
                    };
                    reader.readAsDataURL(input.files[0]);
                    fmmCompressImage(input.files[0], 1024, 0.8).then(function (blob) {
                        fmmSetFiles(input, blob, input.files[0].name.replace(/\\.[^.]+$/, '') + '.jpg');
                    }).catch(function () {});
                }
            }
            """),
            Button(_("common.save"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:14px;"),
        ),
        method="post", action=f"/d/{device_id}/fault/{fault['id']}/edit",
        enctype="multipart/form-data",
    )