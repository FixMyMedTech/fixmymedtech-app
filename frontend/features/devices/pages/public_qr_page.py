from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api

from components import *

from components import page_shell, status_badge, fmt_date, pub_shell, map_component
from features.devices.static.guides import category_label, GUIDE_INDEX
from i18n import t as make_t


def _user_can_edit(me, device_org_id):
    """Check if user has admin/technician role in the device's organization."""
    for org in me.get("organizations", []):
        if org["id"] == device_org_id and org.get("role") in ("admin", "technician"):
            return True
    return False
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# PUBLIC QR PAGE
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}")
async def get(req, device_id: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        data = await devices_api.get_device_public(device_id)
    except Exception:
        return pub_shell(
            Div(
                Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                H2(_("public_qr.not_found")),
                P(_("public_qr.not_found_msg")),
                A(_("public_qr.register_new"), href=f"/device/{device_id}/new", cls="btn btn-primary",
                style="margin-top:20px;"),
                style="text-align:center;padding:60px 24px;"
            ),
            lang=lang
        )

    d = data.get("device", {})
    docs = data.get("documents", [])
    faults = data.get("recent_faults", [])
    logs = data.get("recent_logs", [])
    cat = d.get("category") or {}

    maint_slug = cat.get("slug") or d.get("category_id") or ""
    if maint_slug in GUIDE_INDEX:
        user_guide_btn = A(Span("ⓘ", style="font-size:1.3rem;"),
                                    Div(_("public_qr.user_guide")),
                                    href=f"/device/maintenace_guide/{maint_slug}",
                                    cls="btn btn-secondary btn-sm",
                                    style="margin-left:6px;justify-content:center;")
        maint_guide_btn = A(Span("🔧", style="font-size:1.3rem;"),
                            Div(_("public_qr.maint_guide")),
                            href=f"/device/maintenace_guide/{maint_slug}",
                            cls="btn btn-secondary btn-sm",
                            style="margin-left:6px;justify-content:center;")
    else:
        user_guide_btn = Button(Span("ⓘ", style="font-size:1.3rem;"),
                                         Div(_("public_qr.user_guide")),
                                         disabled=True,
                                         cls="btn btn-secondary btn-sm",
                                         style="margin-left:6px;justify-content:center;opacity:.5;cursor:not-allowed;")
        
        maint_guide_btn = Button(Span("🔧", style="font-size:1.3rem;"),
                                 Div(_("public_qr.maint_guide")),
                                 disabled=True,
                                 cls="btn btn-secondary btn-sm",
                                 style="margin-left:6px;justify-content:center;opacity:.5;cursor:not-allowed;")

    nm = d.get("next_maintenance","")
    import datetime
    overdue = nm and nm < datetime.datetime.now().isoformat()

    doc_items = [
        A(
            Span("▶" if doc.get("type")=="video" else "📄" if doc.get("type")=="manual" else "📋",
                 style="font-size:1.2rem;"),
            Div(
                Div(doc.get("title",""), style="font-weight:500;font-size:0.875rem;"),
                Div(f"{doc.get('type','')} · {doc.get('language','').upper()}",
                    style="font-size:0.75rem;color:var(--c-text-3);"),
            ),
            href=doc.get("url","#"), target="_blank",
            style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-md);text-decoration:none;color:var(--c-text);margin-bottom:8px;"
        ) for doc in docs
    ]

    fault_items = [
        A(
            Div(
                Div(
                    status_badge(f.get("severity","medium"), "severity", lang=lang),
                    status_badge(f.get("status","open"), "fault", lang=lang),
                    Span(fmt_date(f.get("reported_at","")),
                         style="font-size:0.72rem;color:var(--c-text-3);"),
                    style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;"
                ),
                P(f.get("description",""), style="font-size:0.875rem;margin:0 0 10px;"),
                Div(_("public_qr.view_fault") + " →", cls="btn btn-secondary btn-sm",
                    style="justify-content:center;"),
                style="background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-md);padding:12px;"
            ),
            href=f"/d/{device_id}/fault/{f['id']}",
            style="text-decoration:none;color:var(--c-text);display:block;margin-bottom:8px;"
        ) for f in faults
    ]

    log_items = [
        A(
            Div(
                Div(
                    status_badge(l.get("status", "open"), "log", lang=lang),
                    Span(_(f"maintenance_log.type_{l.get('type', 'preventive')}"),
                         cls="badge badge-blue"),
                    Span(fmt_date(l.get("performed_at","")),
                         style="font-size:0.72rem;color:var(--c-text-3);"),
                    style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;"
                ),
                P(l.get("description","") or _("log_detail.no_description"),
                  style="font-size:0.875rem;margin:0 0 10px;"),
                Div(_("public_qr.view_log") + " →", cls="btn btn-secondary btn-sm",
                    style="justify-content:center;"),
                style="background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-md);padding:12px;"
            ),
            href=f"/d/{device_id}/log/{l['id']}",
            style="text-decoration:none;color:var(--c-text);display:block;margin-bottom:8px;"
        ) for l in logs
    ]

    content = Div(
        # Header
        Div(
            Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"),
            cls="pub-header"
        ),
        # Device identity
        Div(
            Div(cat.get("icon","🏥"), cls="dev-icon"),
            Div(
                Div(category_label(cat, lang), cls="dev-cat"),
                Div(d.get("name",""), cls="dev-name"),
                Div(f"{d.get('manufacturer','')}{_('common.sn_prefix')}{d.get('serial_number','')}".strip(" ·"),
                    cls="dev-meta"),
            ),
            Div(
                status_badge(d.get("status","operational"), lang=lang),
                Div(d.get("location",""), cls="dev-loc"),
                cls="dev-status"
            ),
            cls="device-identity"
        ),
        # Maintenance warning
        Div(
            Span("⚠", style="font-size:1rem;flex-shrink:0;"),
            Div(
                Strong(_("public_qr.maint_overdue")),
                P(f"{_('public_qr.maint_due')}{fmt_date(nm)}{_('public_qr.maint_contact')}"),
            ),
            A(_("public_qr.maintenance_log_btn"), href=f"/d/{device_id}/maintenance-log",
              cls="btn btn-primary btn-sm",
              style="flex-shrink:0;margin-left:auto;justify-content:center;"),
            cls="warn-bar"
        ) if overdue else "",
        # Manuals
        Div(
            Div(
                Strong(_("public_qr.more_info"), style="font-size:0.875rem;"),
                P(_("public_qr.guidelines"), style="font-size:0.8rem;margin:2px 0 0;"),
            ),
            user_guide_btn,
            # maint_guide_btn,
            cls="report-cta"
        ),
        # Report fault CTA
        Div(
            Div(
                Strong(_("public_qr.found_problem"), style="font-size:0.875rem;"),
                P(_("public_qr.report_cta"), style="font-size:0.8rem;margin:2px 0 0;"),
            ),
            A(_("public_qr.report_btn"), href=f"/d/{device_id}/report",
              cls="btn btn-danger btn-sm"),
            cls="report-cta"
        ),
        # Device info
        Div(
            H3(_("public_qr.info"),
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            Dl(
                *[Div(Dt(k), Dd(v), cls="info-row")
                  for k, v in [
                      (_("public_qr.status"),       d.get("status", _("common.fallback"))),
                      (_("public_qr.location"),     d.get("location", _("common.fallback"))),
                      (_("public_qr.manufacturer"), d.get("manufacturer", _("common.fallback"))),
                      (_("public_qr.model"),        d.get("model", _("common.fallback"))),
                      (_("public_qr.serial"),       d.get("serial_number", _("common.fallback"))),
                      (_("public_qr.last_maint"),   fmt_date(d.get("last_maintenance",""))),
                      (_("public_qr.next_maint"),   fmt_date(nm)),
                  ]],
                cls="info-list"
            ),
            cls="pub-section"
        ),
        # Map
        Div(
            H3(_("public_qr.location_map"),
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            map_component(
                lat=d.get("latitude", 0),
                lng=d.get("longitude", 0),
                markers=[{"lat": d["latitude"], "lng": d["longitude"], "title": d.get("name","")}],
                height="250px"
            ),
            cls="pub-section"
        ) if d.get("latitude") is not None and d.get("longitude") is not None else "",
        # Manuals
        Div(
            H3(_("public_qr.documents"),
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            *doc_items if doc_items else [P(_("public_qr.no_docs"), style="color:var(--c-text-3);font-size:0.875rem;")],
            cls="pub-section"
        ) if docs else "",
        # Recent faults
        Div(
            H3(_("public_qr.faults"),
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            *fault_items if fault_items else [P(_("public_qr.no_faults"), style="color:var(--c-text-3);font-size:0.875rem;")],
            cls="pub-section"
        ),
        # Recent maintenance logs
        Div(
            H3(_("public_qr.logs"),
               style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;"),
            *log_items if log_items else [P(_("public_qr.no_logs"), style="color:var(--c-text-3);font-size:0.875rem;")],
            cls="pub-section"
        ),
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{d.get('name', _('common.device'))} — {_('brand')}", lang=lang)


# ══════════════════════════════════════════════════════════════
# PUBLIC FAULT REPORT DETAIL
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
        if _user_can_edit(me, device.get("organization_id")):
            edit_btn = Div(
                A(_("fault_detail.edit"), href=f"/d/{device_id}/fault/{fault['id']}/edit",
                  cls="btn btn-primary", style="width:100%;justify-content:center;"),
                cls="pub-section"
            )

    content = Div(
        # Header
        Div(
            Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"),
            cls="pub-header"
        ),
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
    if not _user_can_edit(me, fault_device.get("organization_id")):
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
        # Header
        Div(
            Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"),
            cls="pub-header"
        ),
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
# PUBLIC MAINTENANCE LOG DETAIL
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/log/{log_id}", methods=["get"])
async def get_log_public(req, device_id: str, log_id: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        log = await devices_api.get_maintenance_log_public(log_id)
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

    device = log.get("device") or {}
    performed_by = log.get("performed_by_profile") or {}
    assigned = log.get("assigned_to_profile") or {}

    sec_head = lambda t: H3(t,
        style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;")

    rows = [
        (_("log_detail.status"),       status_badge(log.get("status", "open"), "log", lang=lang)),
        (_("log_detail.type"),         _(f"maintenance_log.type_{log.get('type', 'preventive')}")),
        (_("log_detail.performed_at"), fmt_date(log.get("performed_at", ""))),
        (_("log_detail.technician"),   performed_by.get("full_name", _("common.fallback"))),
        (_("log_detail.assigned_to"),  assigned.get("full_name", _("common.fallback"))),
        (_("log_detail.parts_replaced"), log.get("parts_replaced", _("common.fallback"))),
        (_("log_detail.cost"),         f"${log['cost_usd']}" if log.get("cost_usd") else _("common.fallback")),
        (_("log_detail.next_due"),     fmt_date(log.get("next_due", ""))),
    ]

    # Botón editar solo si hay sesión con rol técnico/admin
    edit_btn = ""
    token = auth_helper.get_token(req)
    if token:
        try:
            me = await auth_api.get_me(token)
        except Exception:
            me = {}
        if _user_can_edit(me, device.get("organization_id")):
            edit_btn = Div(
                A(_("log_detail.edit"), href=f"/d/{device_id}/log/{log['id']}/edit",
                  cls="btn btn-primary", style="width:100%;justify-content:center;"),
                cls="pub-section"
            )

    content = Div(
        # Header
        Div(
            Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"),
            cls="pub-header"
        ),
        # Title
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}",
              style="font-size:0.8rem;color:var(--c-text-3);text-decoration:none;margin-bottom:10px;display:inline-block;"),
            Div(f"{device.get('name','')}",
                style="font-size:0.78rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;"),
            H1(_("log_detail.heading"), style="font-family:var(--font-display);font-size:1.25rem;margin:2px 0 0;"),
            cls="pub-section"
        ),
        # Details
        Div(
            sec_head(_("log_detail.info")),
            Dl(
                *[Div(Dt(k), Dd(v), cls="info-row") for k, v in rows],
                cls="info-list", style="padding:0;"
            ),
            cls="pub-section"
        ),
        # Description
        Div(
            sec_head(_("log_detail.description")),
            P(log.get("description", _("log_detail.no_description")),
              style="font-size:0.9rem;white-space:pre-wrap;color:var(--c-text-2);"),
            cls="pub-section"
        ),
        edit_btn,
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{_('log_detail.heading')} — {_('brand')}", lang=lang)


# ══════════════════════════════════════════════════════════════
# PUBLIC MAINTENANCE LOG EDIT
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/log/{log_id}/edit", methods=["get"])
async def get_log_edit(req, device_id: str, log_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/log/{log_id}/edit", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}
    log_obj = await devices_api.get_maintenance_log_public(log_id)
    log_device = (log_obj.get("device") or {}) if isinstance(log_obj, dict) else {}
    if not _user_can_edit(me, log_device.get("organization_id")):
        return RedirectResponse(f"/d/{device_id}/log/{log_id}", status_code=302)

    try:
        log = await devices_api.get_maintenance_log_public(log_id)
    except Exception:
        return RedirectResponse(f"/d/{device_id}", status_code=302)

    device = log.get("device") or {}
    assignees = []
    try:
        assignees = await faults_api.get_fault_assignees(token, device_id)
    except Exception:
        assignees = []

    content = Div(
        # Header
        Div(
            Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"),
            cls="pub-header"
        ),
        # Title
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}/log/{log_id}",
              style="font-size:0.8rem;color:var(--c-text-3);text-decoration:none;margin-bottom:10px;display:inline-block;"),
            Div(f"{device.get('name','')}",
                style="font-size:0.78rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;"),
            H1(_("log_detail.edit"), style="font-family:var(--font-display);font-size:1.25rem;margin:2px 0 0;"),
            cls="pub-section"
        ),
        _log_edit_form(log, device_id, assignees, lang),
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{_('log_detail.edit')} — {_('brand')}", lang=lang)


@rt("/d/{device_id}/log/{log_id}/edit", methods=["post"])
async def post_log_edit(req, device_id: str, log_id: str, type: str = "",
                        status: str = "", assigned_to: str = "", description: str = "",
                        parts_replaced: str = "", cost_usd: str = "",
                        next_due: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/log/{log_id}/edit", status_code=302)

    data = {}
    if type:
        data["type"] = type
    if status:
        data["status"] = status
    if assigned_to:
        data["assigned_to"] = assigned_to
    if description is not None:
        data["description"] = description
    if parts_replaced is not None:
        data["parts_replaced"] = parts_replaced
    if cost_usd:
        data["cost_usd"] = cost_usd
    if next_due:
        data["next_due"] = next_due
    try:
        await devices_api.update_maintenance_log(token, log_id, data)
    except Exception:
        pass

    return RedirectResponse(f"/d/{device_id}/log/{log_id}", status_code=303)


# ══════════════════════════════════════════════════════════════
# HELPERS: formularios de edición
# ══════════════════════════════════════════════════════════════

def _assignee_options(assignees, current: str = "", lang: str = "en"):
    _ = make_t(lang)
    opts = [Option(_("maintenance_log.assignee_none"), value="",
                   selected=(not current))]
    for a in assignees:
        role_label = _("role." + (a.get("role") or "technician"))
        opts.append(Option(
            f"{a.get('full_name','')} — {role_label}",
            value=a["id"],
            selected=(str(a["id"]) == str(current)),
        ))
    return opts


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
                Select(*_assignee_options(assignees, fault.get("assigned_to") or "", lang),
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
                    reader.onload = function (e) { preview.src = e.target.result; };
                    reader.readAsDataURL(input.files[0]);
                }
            }
            """),
            Button(_("common.save"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:14px;"),
        ),
        method="post", action=f"/d/{device_id}/fault/{fault['id']}/edit",
        enctype="multipart/form-data",
    )


def _log_edit_form(log, device_id, assignees, lang):
    _ = make_t(lang)
    sec_head = lambda t: H3(t,
        style="font-size:0.75rem;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--c-text-3);margin-bottom:8px;")
    return Form(
        Div(
            sec_head(_("log_detail.edit")),
            Div(
                Label(_("log_detail.status"), cls="label"),
                Select(*[Option(_(f"badge.{v}"), value=v,
                                selected=(log.get("status", "open") == v))
                         for v in ["open", "in_progress", "closed"]],
                       name="status", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.type"), cls="label"),
                Select(*[Option(_(f"maintenance_log.type_{v}"), value=v,
                                selected=(log.get("type") == v))
                         for v in ["preventive", "corrective", "inspection"]],
                       name="type", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.assigned_to"), cls="label"),
                Select(*_assignee_options(assignees, log.get("assigned_to") or "", lang),
                       name="assigned_to", cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.description"), cls="label"),
                Textarea(log.get("description", ""), name="description", rows="3",
                         cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.parts_replaced"), cls="label"),
                Input(type="text", name="parts_replaced", value=log.get("parts_replaced", ""),
                      cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.cost"), cls="label"),
                Input(type="number", step="0.01", name="cost_usd",
                      value=log.get("cost_usd", ""), cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Div(
                Label(_("log_detail.next_due"), cls="label"),
                Input(type="date", name="next_due",
                      value=str(log.get("next_due", ""))[:10], cls="input"),
                cls="form-group", style="margin-top:10px;"
            ),
            Button(_("common.save"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:14px;"),
        ),
        method="post", action=f"/d/{device_id}/log/{log['id']}/edit",
    )
