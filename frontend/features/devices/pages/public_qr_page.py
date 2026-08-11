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

from components import page_shell, status_badge, fmt_date, pub_shell, map_component
from features.devices.static.guides import category_label, GUIDE_INDEX
from i18n import t as make_t
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
        Div(
            Div(
                status_badge(f.get("severity","medium"), "severity", lang=lang),
                status_badge(f.get("status","open"), "fault", lang=lang),
                Span(fmt_date(f.get("reported_at","")),
                     style="font-size:0.72rem;color:var(--c-text-3);"),
                style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;"
            ),
            P(f.get("description",""), style="font-size:0.875rem;margin:0;"),
            style="background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--r-md);padding:12px;margin-bottom:8px;"
        ) for f in faults
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
        # Footer
        Div(_("brand_footer"), cls="pub-footer"),
        cls="pub-page"
    )

    return pub_shell(content, title=f"{d.get('name', _('common.device'))} — {_('brand')}", lang=lang)
