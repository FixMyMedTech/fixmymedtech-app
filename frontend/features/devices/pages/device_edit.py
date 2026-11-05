from typing import Optional
from fasthtml.common import *
from starlette.responses import RedirectResponse
import httpx

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.devices.api as devices_api
import features.faults.api as faults_api
import features.maintenance.api as maintenance_api
import features.groups.api as org_api

from components import page_shell, alert as alert_box, assignee_options, fmt_date, status_badge, map_component
from i18n import t as make_t
from features.devices.static.guides import category_label
from features.documents.components import DOCS_CSS, doc_list, ifixit_picker, upload_form

rt = APIRouter()

STATUSES = ("operational", "maintenance", "fault", "decommissioned")
ACQUISITION_TYPES = ("purchased", "donated", "leased")
FAULT_STATUSES = ("open", "assigned", "in_progress", "resolved")
FAULT_SEVERITIES = ("low", "medium", "high", "critical")
LOG_STATUSES = ("open", "in_progress", "closed")
LOG_TYPES = ("preventive", "corrective", "inspection")

EDIT_DEVICE_JS = """
function toggleDeviceCard(id) {
  var display = document.getElementById(id + '-display');
  var edit = document.getElementById(id + '-edit');
  if (!display || !edit) return;
  var editing = edit.style.display !== 'none';
  display.style.display = editing ? '' : 'none';
  edit.style.display = editing ? 'none' : 'block';
}
function captureDeviceLoc() {
  if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
  navigator.geolocation.getCurrentPosition(function (pos) {
    document.getElementById('device-lat').value = pos.coords.latitude;
    document.getElementById('device-lng').value = pos.coords.longitude;
  }, function (err) { alert('Geolocation error: ' + err.message); });
}
"""

SAVED_MESSAGES = {
    "1": "device_edit.saved",
    "photo": "device_edit.photo_saved",
    "fault": "device_edit.fault_saved",
    "log": "device_edit.log_saved",
}

ROW_STYLE = ("display:flex;justify-content:space-between;padding:8px 0;"
             "border-bottom:1px solid var(--c-border);font-size:0.875rem;")


# ══════════════════════════════════════════════════════════════
# HELPERS (mirroring device_detail)
# ══════════════════════════════════════════════════════════════

def _org_loc(org: dict) -> str:
    bits = []
    if org.get("country"):
        bits.append(str(org["country"]))
    if org.get("region"):
        bits.append(str(org["region"]))
    if org.get("address"):
        bits.append(str(org["address"]))
    return " · ".join(bits)


def _detail_row(label, value):
    return Div(Dt(label, style="color:var(--c-text-3);font-weight:500;"), Dd(value),
               style=ROW_STYLE)


def _edit_row(label, control):
    return Div(Dt(label, style="color:var(--c-text-3);font-weight:500;"), Dd(control),
               style=ROW_STYLE)


def _edit_button(card_id, _):
    return Button(_("groups.edit"), type="button", cls="btn btn-secondary btn-sm",
                  onclick=f"toggleDeviceCard('{card_id}')")


def _save_cancel(card_id, _):
    return (Button(_("groups.save"), type="submit", cls="btn btn-primary btn-sm"),
            Button(_("groups.cancel"), type="button", cls="btn btn-secondary btn-sm",
                   onclick=f"toggleDeviceCard('{card_id}')"))


def _card_header(title, card_id, _):
    return Div(H3(title, style="margin:0;"), _edit_button(card_id, _),
               style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;")


def _own_col(label, o, _):
    name = o.get("name")
    oid = o.get("id")
    return Div(
        Div(label, cls="own-label"),
        Div(
            A(name, href=f"/groups/{oid}/view",
              style="color:var(--c-primary);text-decoration:none;") if oid else (name or ""),
            cls="own-name",
        ) if name else Div(_("common.fallback"), cls="own-name"),
        cls="own-col",
    )


def _can_manage(device: dict, me: dict) -> bool:
    """Same rule as the backend's _can_edit_device: admin of the owning
    organization, admin of the device's healthsite, admin of the organization
    that maintains it, or the user who registered the device."""
    return auth_helper.can_edit_device(me, device)


# ══════════════════════════════════════════════════════════════
# CARDS (same structure as the device detail page)
# ══════════════════════════════════════════════════════════════

def _ownership_card(device: dict, me: dict, my_orgs: list, all_orgs: list, _):
    """healthsite: my_orgs (my memberships). maintenance org: only the
    engineering organizations — the ones that actually service equipment."""
    card_id = "ownership"
    org = device.get("organization") or {}
    maint_org = device.get("organization_maintenance") or {}
    hs = device.get("healthsite") or {}

    display = Div(
        Div(H3(_("device_detail.ownership"), style="margin-bottom:12px;")),
        Div(
            _own_col(_("device_detail.responsible_org"), org, _),
            _own_col(_("device_detail.maintenance_org"), maint_org, _),
            _own_col(_("device_detail.healthsite"), hs, _),
            cls="own-grid",
        ),
        id=f"{card_id}-display",
    )

    can_set_maint = auth_helper.can_set_maintenance_org(me, device)
    current_hs = str(device.get("healthsite_id") or "")

    hs_options = [Option(_("new_device.select_healthsite"), value="",
                          selected=not device.get("healthsite_id"))]
    hs_ids = {str(o["id"]) for o in my_orgs}
    if current_hs and current_hs not in hs_ids:
        # Current healthsite is not one of my orgs — keep it selectable so a
        # save doesn't silently clear it.
        hs_options.append(Option(hs.get("name") or current_hs, value=current_hs, selected=True))
    hs_options += [
        Option(o.get("name", ""), value=o["id"], selected=(str(o["id"]) == current_hs))
        for o in my_orgs
    ]
    edit_rows = [
        _edit_row(_("device_detail.healthsite"),
                  Select(*hs_options, name="healthsite_id", cls="input", style="max-width:260px;")),
    ]
    if can_set_maint:
        current_maint = str(device.get("organization_maintenance_id") or "")
        engineering = [o for o in all_orgs if (o.get("type") or "") == "engineering"]
        maint_options = [
            Option(o.get("name", ""), value=o["id"],
                   selected=(str(o["id"]) == current_maint))
            for o in engineering
        ]
        if current_maint and current_maint not in {str(o["id"]) for o in engineering}:
            # Same guard as the healthsite select: never drop the current value.
            maint_options.insert(0, Option(maint_org.get("name") or current_maint,
                                           value=current_maint, selected=True))
        edit_rows.append(
            _edit_row(_("device_detail.maintenance_org"),
                      Select(*maint_options, name="organization_maintenance_id",
                             cls="input", style="max-width:260px;")),
        )

    save, cancel = _save_cancel(card_id, _)
    edit = Form(Dl(*edit_rows), save, cancel,
                method="post", action=f"/devices/{device['id']}/edit",
                id=f"{card_id}-edit", style="display:none;")
    return Div(
        _card_header(_("device_detail.ownership"), card_id, _),
        display, edit,
        cls="card", style="margin-bottom:16px;",
    )


def _info_card(device: dict, categories: list, lang: str, _):
    card_id = "info"
    display = Div(
        Dl(
            _detail_row(_("device_detail.serial"),
                        device.get("serial_number", _("common.fallback"))),
            _detail_row(_("device_detail.manufacturer"),
                        device.get("manufacturer", _("common.fallback"))),
            _detail_row(_("device_detail.model"),
                        device.get("model", _("common.fallback"))),
            _detail_row(_("device_detail.year"),
                        str(device.get("manufacture_year", _("common.fallback")))),
        ),
        id=f"{card_id}-display",
    )
    cat_options = [
        Option(_("device_list.col_category"), value="", selected=not device.get("category_id")),
        *[
            Option(f"{c.get('icon', '')} {category_label(c, lang)}".strip(), value=c.get("slug"),
                   selected=(c.get("slug") == device.get("category_id")))
            for c in categories
        ],
    ]
    save, cancel = _save_cancel(card_id, _)
    edit = Form(
        Dl(
            _edit_row(_("new_device.name_label"),
                      Input(name="name", value=device.get("name", ""), cls="input", style="max-width:260px;")),
            _edit_row(_("device_list.col_category"),
                      Select(*cat_options, name="category_id", cls="input", style="max-width:260px;")),
            _edit_row(_("device_detail.serial"),
                      Input(name="serial_number", value=device.get("serial_number") or "",
                            cls="input", style="max-width:260px;")),
            _edit_row(_("device_detail.manufacturer"),
                      Input(name="manufacturer", value=device.get("manufacturer") or "",
                            cls="input", style="max-width:260px;")),
            _edit_row(_("device_detail.model"),
                      Input(name="model", value=device.get("model") or "",
                            cls="input", style="max-width:260px;")),
            _edit_row(_("device_detail.year"),
                      Input(name="manufacture_year", type="number",
                            value=device.get("manufacture_year") or "",
                            cls="input", style="max-width:120px;")),
        ),
        save, cancel,
        method="post", action=f"/devices/{device['id']}/edit",
        id=f"{card_id}-edit", style="display:none;",
    )
    return Div(
        _card_header(_("device_detail.info"), card_id, _),
        display, edit,
        cls="card",
    )


def _maintenance_card(device: dict, _):
    card_id = "maintenance"
    acq = f"{device.get('acquisition_type', _('common.fallback'))} · {fmt_date(device.get('acquisition_date', ''))}"
    display = Div(
        Dl(
            _detail_row(_("device_detail.status"), device.get("status", _("common.fallback"))),
            _detail_row(_("device_detail.acquisition"), acq),
            _detail_row(_("device_detail.last_maint"), fmt_date(device.get("last_maintenance", ""))),
            _detail_row(_("device_detail.next_maint"), fmt_date(device.get("next_maintenance", ""))),
        ),
        id=f"{card_id}-display",
    )
    save, cancel = _save_cancel(card_id, _)
    edit = Form(
        Dl(
            _edit_row(_("device_detail.status"), Select(
                *[Option(_(f"new_device.status_{value}"), value=value,
                         selected=(device.get("status") == value)) for value in STATUSES],
                name="status", cls="input", style="max-width:260px;")),
            _edit_row(_("new_device.acquisition_label"), Select(
                *[Option(_(f"new_device.acquisition_{value}"), value=value,
                         selected=(device.get("acquisition_type") == value)) for value in ACQUISITION_TYPES],
                name="acquisition_type", cls="input", style="max-width:260px;")),
            _edit_row(_("new_device.acquisition_date"),
                      Input(name="acquisition_date", type="date",
                            value=(device.get("acquisition_date") or "")[:10],
                            cls="input", style="max-width:260px;")),
            _edit_row(_("device_detail.last_maint"),
                      Input(name="last_maintenance", type="date",
                            value=(device.get("last_maintenance") or "")[:10],
                            cls="input", style="max-width:260px;")),
            _edit_row(_("device_detail.next_maint"),
                      Input(name="next_maintenance", type="date",
                            value=(device.get("next_maintenance") or "")[:10],
                            cls="input", style="max-width:260px;")),
            _edit_row(_("new_device.notes"),
                      Textarea(device.get("notes") or "", name="notes", rows="4",
                               cls="input", style="max-width:420px;")),
        ),
        save, cancel,
        method="post", action=f"/devices/{device['id']}/edit",
        id=f"{card_id}-edit", style="display:none;",
    )
    return Div(
        _card_header(_("device_detail.maintenance"), card_id, _),
        display, edit,
        cls="card",
    )


def _photo_card(device: dict, device_id: str, _):
    has_photo = bool(device.get("photo_key"))
    variant = device.get("photo_public_variant", "processed")
    cache_key = device.get("photo_key") if variant == "original" else (
        device.get("photo_processed_key") or device.get("photo_key"))
    preview = (
        Img(src=f"/device/{device_id}/photo?v={cache_key or 'original'}",
            alt=device.get("name", ""),
            style="width:100%;max-height:360px;object-fit:cover;border-radius:var(--r-md);")
        if has_photo else
        P(_("device_edit.no_photo"), style="font-size:0.85rem;color:var(--c-text-3);margin:0 0 10px;")
    )
    form = Form(
        preview,
        P(_("device_detail.photo_public_choice"),
          style="font-size:0.8rem;color:var(--c-text-3);margin:8px 0;"),
        Div(
            Button(_("device_detail.photo_processed"), type="submit", name="variant", value="processed",
                   cls="btn btn-primary btn-sm" if variant == "processed" else "btn btn-secondary btn-sm"),
            Button(_("device_detail.photo_original"), type="submit", name="variant", value="original",
                   cls="btn btn-primary btn-sm" if variant == "original" else "btn btn-secondary btn-sm"),
            style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px;",
        ) if has_photo else "",
        Div(
            Label(_("fault_detail.change_photo"), cls="label", for_="device-photo"),
            Input(type="file", id="device-photo", name="photo", accept="image/*", cls="input"),
            style="margin-top:12px;",
        ),
        Button(_("common.save"), type="submit", cls="btn btn-primary btn-sm",
               style="margin-top:12px;"),
        method="post", action=f"/devices/{device_id}/edit/photo",
        enctype="multipart/form-data",
    )
    return Div(
        H3(_("device_detail.photo"), style="margin-bottom:12px;"),
        form,
        cls="card", style="margin-bottom:16px;",
    )


def _map_card(device: dict, device_id: str, _):
    card_id = "map"
    hs = device.get("healthsite") or {}
    lat, lng = device.get("latitude"), device.get("longitude")

    display = Div(
        Div(
            P(device.get("location", _("common.fallback")), style="font-size:0.85rem;margin:2px 0 0;"),
            Div(hs.get("name", ""), style="font-weight:600;font-size:0.9rem;"),
            P(_org_loc(hs), style="color:var(--c-text-3);font-size:0.85rem;margin:2px 0 0;")
            if _org_loc(hs) else "",
        ) if hs.get("name") else
        P(device.get("location", _("common.fallback")), style="font-size:0.85rem;margin:2px 0 0;"),
        map_component(
            lat=lat if lat is not None else 0,
            lng=lng if lng is not None else 0,
            markers=[{"lat": lat, "lng": lng, "title": device.get("name", "")}],
            height="300px",
        ) if lat is not None and lng is not None else "",
        id=f"{card_id}-display",
    )
    save, cancel = _save_cancel(card_id, _)
    edit = Form(
        Dl(
            _edit_row(_("new_device.location"),
                      Input(name="location", value=device.get("location") or "",
                            cls="input", style="max-width:260px;")),
            _edit_row(_("device_edit.coords"), Div(
                Input(name="latitude", id="device-lat",
                      value=lat if lat is not None else "",
                      cls="input", placeholder="Latitude", style="max-width:150px;"),
                Input(name="longitude", id="device-lng",
                      value=lng if lng is not None else "",
                      cls="input", placeholder="Longitude", style="max-width:150px;"),
                Button("📍 " + _("device_detail.capture_location"), type="button",
                       cls="btn btn-secondary btn-sm", onclick="captureDeviceLoc()",
                       style="white-space:nowrap;"),
                style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;",
            )),
        ),
        save, cancel,
        method="post", action=f"/devices/{device_id}/edit",
        id=f"{card_id}-edit", style="display:none;",
    )
    return Div(
        _card_header(_("device_detail.location_map"), card_id, _),
        display, edit,
        cls="card", style="margin-bottom:16px;",
    )


# ══════════════════════════════════════════════════════════════
# FAULTS & MAINTENANCE LOGS (same tables as device_detail)
# ══════════════════════════════════════════════════════════════

def _log_edit_row(log: dict, device_id: str, assignees: list, me: dict, lang: str, _):
    if not auth_helper.user_can_edit_log(me, log):
        return []
    form = Form(
        Div(
            Div(Label(_("log_detail.status"), cls="label"),
                Select(*[Option(_(f"badge.{v}"), value=v, selected=(log.get("status", "open") == v))
                         for v in LOG_STATUSES],
                       name="status", cls="input"),
                style="flex:1;min-width:150px;"),
            Div(Label(_("log_detail.type"), cls="label"),
                Select(*[Option(_(f"maintenance_log.type_{v}"), value=v,
                                selected=(log.get("type") == v)) for v in LOG_TYPES],
                       name="type", cls="input"),
                style="flex:1;min-width:150px;"),
            Div(Label(_("log_detail.assigned_to"), cls="label"),
                Select(*assignee_options(assignees, log.get("assigned_to") or "", lang),
                       name="assigned_to", cls="input"),
                style="flex:1;min-width:150px;"),
            style="display:flex;gap:12px;flex-wrap:wrap;",
        ),
        Div(Label(_("log_detail.description"), cls="label"),
            Textarea(log.get("description") or "", name="description", rows="3", cls="input"),
            style="margin-top:10px;"),
        Div(
            Div(Label(_("log_detail.parts_replaced"), cls="label"),
                Input(name="parts_replaced", value=log.get("parts_replaced") or "", cls="input")),
            Div(Label(_("log_detail.cost"), cls="label"),
                Input(type="number", step="0.01", name="cost_usd",
                      value=log.get("cost_usd") or "", cls="input")),
            Div(Label(_("log_detail.next_due"), cls="label"),
                Input(type="date", name="next_due", value=str(log.get("next_due") or "")[:10],
                      cls="input")),
            style="display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;",
        ),
        Button(_("common.save"), type="submit", cls="btn btn-primary btn-sm",
               style="margin-top:12px;"),
        method="post", action=f"/devices/{device_id}/edit/log/{log['id']}",
        style="margin-top:4px;",
    )
    return [Tr(
        Td(
            Details(Summary(_("log_detail.edit"),
                            style="font-size:0.8rem;color:var(--c-text-3);cursor:pointer;"),
                    form),
            colspan="5", style="background:rgba(0,0,0,0.02);",
        )
    )]


def _fault_edit_row(fault: dict, device_id: str, assignees: list, me: dict, lang: str, _):
    if not auth_helper.user_can_edit_fault(me, fault):
        return []
    # Status, assignee, diagnosis, approval and resolution all belong to the
    # workflow on the fault's own page — here the reporter can only correct
    # what was reported.
    form = Form(
        Div(Label(_("fault_detail.severity"), cls="label"),
            Select(*[Option(_(f"badge.{v}"), value=v, selected=(fault.get("severity") == v))
                     for v in FAULT_SEVERITIES],
                   name="severity", cls="input"),
            style="flex:1;min-width:150px;"),
        Div(Label(_("fault_detail.description"), cls="label"),
            Textarea(fault.get("description") or "", name="description", rows="3", cls="input"),
            style="flex:2;min-width:220px;"),
        Div(Label(_("fault_detail.change_photo"), cls="label", for_=f"fault-photo-{fault['id']}"),
            Input(type="file", id=f"fault-photo-{fault['id']}", name="photo",
                  accept="image/*", cls="input"),
            style="flex:1;min-width:150px;"),
        Div(
            Button(_("common.save"), type="submit", cls="btn btn-primary btn-sm"),
            A(_("fault_detail.open_workflow"),
              href=f"/device/{device_id}/fault/{fault['id']}",
              cls="btn btn-secondary btn-sm"),
            style="display:flex;gap:8px;margin-top:12px;",
        ),
        method="post", action=f"/devices/{device_id}/edit/fault/{fault['id']}",
        enctype="multipart/form-data",
        style="margin-top:4px;",
    )
    return [Tr(
        Td(
            Details(Summary(_("fault_detail.edit"),
                            style="font-size:0.8rem;color:var(--c-text-3);cursor:pointer;"),
                    form),
            colspan="6", style="background:rgba(0,0,0,0.02);",
        )
    )]


def _history_card(logs: list, device_id: str, assignees: list, me: dict, lang: str, _):
    log_rows = []
    for l in logs:
        log_rows.append(Tr(
            Td(fmt_date(l.get("performed_at", "")), style="font-size:0.875rem;"),
            Td(Span(l.get("type", ""), cls="badge badge-blue")),
            Td(l.get("description", _("common.fallback")), style="font-size:0.875rem;"),
            Td(f"${l['cost_usd']}" if l.get("cost_usd") else _("common.fallback"),
               style="font-size:0.875rem;"),
            Td(A(_("device_list.view"), href=f"/d/{device_id}/log/{l['id']}",
                 cls="btn btn-secondary btn-sm")),
        ))
        log_rows += _log_edit_row(l, device_id, assignees, me, lang, _)
    return Div(
        Div(
            H3(_("device_detail.history"), style="margin:0;"),
            A(_("maintenance_log.submit"), href=f"/d/{device_id}/maintenance-log",
              cls="btn btn-primary btn-sm"),
            style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;",
        ),
        Div(
            Table(
                Thead(Tr(Th(_("device_detail.col_date")), Th(_("device_detail.col_type")),
                         Th(_("device_detail.col_description")), Th(_("device_detail.col_cost")), Th(""))),
                Tbody(*log_rows) if log_rows else Tbody(
                    Tr(Td(_("device_detail.no_maint"), colspan="5",
                        style="color:var(--c-text-3);padding:20px;text-align:center;")))
            ),
            style="border:none;border-radius:0;"
        ),
        cls="card", style="margin-bottom:16px;",
    )


def _faults_card(faults: list, device_id: str, assignees: list, me: dict, lang: str, _):
    fault_rows = []
    for f in faults:
        fault_rows.append(Tr(
            Td(fmt_date(f.get("reported_at", "")), style="font-size:0.875rem;"),
            Td(f.get("reporter_name", _("common.fallback")), style="font-size:0.875rem;"),
            Td(f.get("description", ""), style="font-size:0.875rem;"),
            Td(status_badge(f.get("severity", "medium"), "severity", lang=lang)),
            Td(status_badge(f.get("status", "open"), "fault", lang=lang)),
            Td(A(_("device_list.view"), href=f"/d/{device_id}/fault/{f['id']}",
                 cls="btn btn-secondary btn-sm")),
        ))
        fault_rows += _fault_edit_row(f, device_id, assignees, me, lang, _)
    return Div(
        Div(
            H3(_("device_detail.faults"), style="margin:0;"),
            A(_("report_fault.heading"), href=f"/d/{device_id}/report",
              cls="btn btn-primary btn-sm"),
            style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;",
        ),
        Div(
            Table(
                Thead(Tr(Th(_("device_detail.col_date")), Th(_("device_detail.col_reported_by")),
                         Th(_("device_detail.col_description")), Th(_("device_detail.col_severity")),
                         Th(_("device_detail.col_status")), Th(""))),
                Tbody(*fault_rows) if fault_rows else Tbody(
                    Tr(Td(_("device_detail.no_faults"), colspan="6",
                        style="color:var(--c-text-3);padding:20px;text-align:center;")))
            ),
            style="border:none;border-radius:0;"
        ),
        cls="card",
    )


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

DOC_NOTICES = {
    "attached": ("docs.flash_attached", "success"),
    "uploaded": ("docs.flash_uploaded", "success"),
    "removed": ("docs.flash_removed", "success"),
    "none_selected": ("docs.flash_none_selected", "warning"),
    "error": ("docs.flash_error", "error"),
}


def _documents_card(_, req, device_id, d, docs, lang):
    """Manage the device's documents: remove, attach from iFixit, upload."""
    notice = ""
    key = req.query_params.get("docs")
    if key in DOC_NOTICES:
        text_key, kind = DOC_NOTICES[key]
        detail = req.query_params.get("docs_detail", "")
        notice = Div(_(text_key) + (f" {detail}" if detail else ""), cls=f"alert alert-{kind}")
    query = " ".join(x for x in (d.get("manufacturer"), d.get("model")) if x)
    return Div(
        Style(DOCS_CSS),
        H3(_("docs.heading"), style="margin-bottom:12px;"),
        notice,
        doc_list(_, docs, device_id=device_id, can_remove=True),
        Details(
            Summary(_("docs.find_heading"), style="cursor:pointer;font-weight:600;margin-top:16px;"),
            Form(ifixit_picker(_, query=query, submit_label=_("docs.attach_selected")),
                 method="post", action=f"/device/{device_id}/documents/ifixit",
                 style="margin-top:10px;"),
            open=(key in ("none_selected",)),
        ),
        Details(
            Summary(_("docs.upload_heading"), style="cursor:pointer;font-weight:600;margin-top:12px;"),
            Div(upload_form(_, device_id, lang), style="margin-top:10px;"),
            open=(key == "error"),
        ),
        id="documents", cls="card", style="margin-bottom:16px;",
    )


@rt("/devices/{device_id}/edit")
async def get(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        payload = await devices_api.get_device(token, device_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse("/devices", status_code=302)
    except Exception:
        return RedirectResponse("/devices", status_code=302)

    d = payload.get("device") or {}
    if not d:
        return RedirectResponse("/devices", status_code=302)

    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}
    if not _can_manage(d, me):
        return RedirectResponse(f"/device/{device_id}", status_code=302)

    cat = d.get("category") or {}
    can_set_maint = auth_helper.can_set_maintenance_org(me, d)

    try:
        categories = await devices_api.get_categories()
    except Exception:
        categories = []
    try:
        my_orgs = await org_api.get_my_organizations(token)
    except Exception:
        my_orgs = []
    all_orgs = []
    if can_set_maint:
        try:
            all_orgs = await org_api.get_organizations(token)
        except Exception:
            all_orgs = []

    faults = list(payload.get("fault_reports") or [])
    logs = list(payload.get("maintenance_logs") or [])
    try:
        all_faults = await faults_api.list_faults(token)
        faults = [f for f in all_faults if str(f.get("device_id")) == str(device_id)]
    except Exception:
        pass
    faults.sort(key=lambda f: f.get("reported_at") or "", reverse=True)

    assignees = []
    if faults or logs:
        try:
            assignees = await faults_api.get_fault_assignees(token, device_id)
        except Exception:
            assignees = []

    saved = req.query_params.get("saved")
    flash = alert_box(_(SAVED_MESSAGES[saved]), "success") if saved in SAVED_MESSAGES else ""

    content = Div(
        Script(EDIT_DEVICE_JS),
        flash,
        A(_("device_detail.back"), href="/devices",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:14px;display:inline-block;"),
        Div(
            Div(
                Div(f"{cat.get('icon', '🏥')} {category_label(cat, lang)}",
                    style="font-size:0.8rem;color:var(--c-text-3);margin-bottom:4px;"),
                H1(d.get("name", ""), style="margin-bottom:4px;"),
                P(f"{d.get('manufacturer', '')} {d.get('model', '')} · {d.get('location', _('device_detail.no_location'))}",
                  style="color:var(--c-text-3);"),
            ),
            Div(status_badge(d.get("status", "operational"), lang=lang),
                style="flex-shrink:0;"),
            cls="page-header", style="margin-bottom:14px;"
        ),
        _ownership_card(d, me, my_orgs, all_orgs, _),
        Div(_info_card(d, categories, lang, _), _maintenance_card(d, _),
            cls="two-col", style="margin-bottom:16px;"),
        Div(_photo_card(d, device_id, _), _map_card(d, device_id, _),
            cls="two-col", style="margin-bottom:16px;"),
        _documents_card(_, req, device_id, d, payload.get("documents") or [], lang),
        _history_card(logs, device_id, assignees, me, lang, _),
        _faults_card(faults, device_id, assignees, me, lang, _),
    )
    return page_shell(content, current="/devices", title=_("device_edit.title"), lang=lang)


@rt("/devices/{device_id}/edit")
async def post(req, device_id: str,
               name: Optional[str] = None, category_id: Optional[str] = None,
               manufacturer: Optional[str] = None, model: Optional[str] = None,
               serial_number: Optional[str] = None, manufacture_year: Optional[str] = None,
               status: Optional[str] = None, location: Optional[str] = None,
               latitude: Optional[str] = None, longitude: Optional[str] = None,
               notes: Optional[str] = None,
               last_maintenance: Optional[str] = None,
               next_maintenance: Optional[str] = None,
               acquisition_date: Optional[str] = None,
               acquisition_type: Optional[str] = None,
               healthsite_id: Optional[str] = None,
               organization_maintenance_id: Optional[str] = None):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    data = {}

    def text(key, value):
        if value is not None:
            data[key] = value.strip()

    if (name or "").strip():
        data["name"] = name.strip()
    if (category_id or "").strip():
        data["category_id"] = category_id.strip()
    text("manufacturer", manufacturer)
    text("model", model)
    text("serial_number", serial_number)
    text("location", location)
    text("notes", notes)
    if status in STATUSES:
        data["status"] = status
    if acquisition_type in ACQUISITION_TYPES:
        data["acquisition_type"] = acquisition_type
    if (manufacture_year or "").strip():
        try:
            data["manufacture_year"] = int(manufacture_year.strip())
        except ValueError:
            pass
    for key, value in (("latitude", latitude), ("longitude", longitude)):
        if (value or "").strip():
            try:
                data[key] = float(value.strip())
            except ValueError:
                pass
    for key, value in (("last_maintenance", last_maintenance),
                       ("next_maintenance", next_maintenance),
                       ("acquisition_date", acquisition_date)):
        if (value or "").strip():
            data[key] = value.strip()
    if healthsite_id is not None:
        data["healthsite_id"] = healthsite_id.strip() or None
    if (organization_maintenance_id or "").strip():
        data["organization_maintenance_id"] = organization_maintenance_id.strip()

    try:
        await devices_api.update_device(token, device_id, data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse(f"/device/{device_id}", status_code=303)
    except Exception:
        return RedirectResponse(f"/device/{device_id}", status_code=303)

    return RedirectResponse(f"/devices/{device_id}/edit?saved=1", status_code=303)


@rt("/devices/{device_id}/edit/photo")
async def post_photo(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    try:
        form = await req.form()
    except Exception:
        form = {}

    variant = form.get("variant")
    if variant in ("processed", "original"):
        try:
            await devices_api.update_device_photo_variant(token, device_id, variant)
        except Exception:
            pass

    photo = form.get("photo")
    if photo is not None and getattr(photo, "filename", ""):
        try:
            content = await photo.read()
        except Exception:
            content = b""
        if content:
            try:
                await devices_api.upload_device_photo(
                    token, device_id,
                    photo.filename or "device_photo.jpg",
                    content, photo.content_type,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    auth_helper.clear_session(req)
                    return RedirectResponse("/login?expired=1", status_code=302)

    return RedirectResponse(f"/devices/{device_id}/edit?saved=photo", status_code=303)


@rt("/devices/{device_id}/edit/fault/{fault_id}")
async def post_fault(req, device_id: str, fault_id: str, severity: str = "",
                     description: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    try:
        fault_obj = await faults_api.get_fault_public(fault_id)
    except Exception:
        return RedirectResponse(f"/devices/{device_id}/edit", status_code=303)
    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}
    if not auth_helper.user_can_edit_fault(me, fault_obj):
        return RedirectResponse(f"/device/{device_id}", status_code=303)

    # Severity and description only — status, assignee and resolution are
    # workflow steps with their own authorizers on the fault's own page.
    data = {}
    if severity in FAULT_SEVERITIES:
        data["severity"] = severity
    data["description"] = description
    try:
        await faults_api.update_fault(token, fault_id, data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
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

    return RedirectResponse(f"/devices/{device_id}/edit?saved=fault", status_code=303)


@rt("/devices/{device_id}/edit/log/{log_id}")
async def post_log(req, device_id: str, log_id: str, type: str = "", status: str = "",
                   assigned_to: str = "", description: str = "",
                   parts_replaced: str = "", cost_usd: str = "", next_due: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    try:
        log_obj = await maintenance_api.get_maintenance_log_public(log_id)
    except Exception:
        return RedirectResponse(f"/devices/{device_id}/edit", status_code=303)
    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}
    if not auth_helper.user_can_edit_log(me, log_obj):
        return RedirectResponse(f"/device/{device_id}", status_code=303)

    data = {}
    if type in LOG_TYPES:
        data["type"] = type
    if status in LOG_STATUSES:
        data["status"] = status
    if assigned_to:
        data["assigned_to"] = assigned_to
    data["description"] = description
    data["parts_replaced"] = parts_replaced
    if (cost_usd or "").strip():
        try:
            data["cost_usd"] = float(cost_usd)
        except ValueError:
            pass
    if (next_due or "").strip():
        data["next_due"] = next_due.strip()
    try:
        await maintenance_api.update_maintenance_log(token, log_id, data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
    except Exception:
        pass

    return RedirectResponse(f"/devices/{device_id}/edit?saved=log", status_code=303)
