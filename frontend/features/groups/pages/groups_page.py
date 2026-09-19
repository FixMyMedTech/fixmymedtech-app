from fasthtml.common import *
from starlette.responses import RedirectResponse
import httpx
import features.groups.api as groups_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell, status_badge

rt = APIRouter()

GEOLOC_JS = """
function fillLocation(){
  if(!navigator.geolocation){ alert('Geolocation not supported'); return; }
  navigator.geolocation.getCurrentPosition(function(p){
    document.getElementById('hs-lat').value = p.coords.latitude.toFixed(6);
    document.getElementById('hs-lng').value = p.coords.longitude.toFixed(6);
  }, function(){ alert('Unable to get your location'); });
}
function pickHS(el){
  document.getElementById('hs-osm-id').value = el.dataset.osmId || '';
  document.getElementById('hs-osm-type').value = el.dataset.osmType || '';
  document.getElementById('hs-name').value = el.dataset.name || '';
  document.getElementById('hs-country').value = el.dataset.country || '';
  document.getElementById('hs-region').value = el.dataset.region || '';
  document.getElementById('hs-address').value = el.dataset.address || '';
  document.getElementById('hs-submit').disabled = false;
}
document.addEventListener('submit', function(e){
  var f = e.target;
  if (f && f.id === 'hs-search-form') {
    var l = document.getElementById('hs-loading');
    var b = document.getElementById('hs-scan-btn');
    if (l) l.style.display = 'flex';
    if (b) b.disabled = true;
  }
});
"""


def _flash(req):
    flash = req.query_params.get("flash", "")
    ok = req.query_params.get("ok", "")
    if not flash:
        return ""
    color = "var(--c-green)" if ok == "1" else "var(--c-danger)"
    return Div(flash, style=f"color:{color};font-size:0.875rem;margin-bottom:14px;")


def _source_badge(source: str, _):
    if source == "healthsites.io":
        return Span(_("groups.source_imported"), cls="badge badge-blue")
    return Span(_("groups.source_app"), cls="badge badge-green")


def _loc_str(org: dict) -> str:
    bits = []
    if org.get("region"):
        bits.append(str(org["region"]))
    if org.get("address"):
        bits.append(str(org["address"]))
    return (" · " + " · ".join(bits)) if bits else ""


def _org_card(org: dict, _):
    is_admin = org.get("role") == "admin"
    loc = _loc_str(org)
    card_actions = Div(
        A(_("groups.view"), href=f"/groups/{org['id']}/view",
          cls="btn btn-secondary btn-sm"),
        A(_("groups.manage"), href=f"/groups/{org['id']}",
          cls="btn btn-primary btn-sm") if is_admin else "",
        style="display:flex;gap:8px;margin-top:12px;",
    )

    return Div(
        Div(
            Div(
                H3(org.get("name", ""), style="margin:0 0 4px 0;font-size:1.1rem;"),
                P(f"{_('groups.country')}: {org.get('country', '') or '—'} {loc}",
                  style="color:var(--c-text-3);font-size:0.85rem;margin:0;"),
                style="flex:1;min-width:0;",
            ),
            Div(
                status_badge(org.get("role") or "member", "fault") if org.get("role") else "",
                _source_badge(org.get("source", "app"), _),
                style="flex-shrink:0;margin-left:12px;display:flex;flex-direction:column;gap:4px;align-items:flex-end;",
            ),
            style="display:flex;flex-wrap:wrap;align-items:flex-start;gap:12px;",
        ),
        card_actions,
        cls="card",
    )


def _org_dialog(_):
    return Dialog(
        Div(
            H3(_("groups.modal_org_title"), style="margin:0 0 4px 0;font-size:1.05rem;"),
            P(_("groups.modal_org_desc"),
              style="color:var(--c-text-3);font-size:0.8rem;margin:0 0 10px 0;"),
            Form(
                Div(
                    Div(
                        Div(Label(_("groups.name"), cls="label"),
                            Div(Input(name="name", cls="input", placeholder=_("groups.site_name_placeholder")),
                                style="display:flex;flex-direction:column;")),
                        Div(Label(_("groups.type"), cls="label"),
                            Div(Select(
                                    Option(_("groups.type_hospital"), value="hospital", selected=True),
                                    Option(_("groups.type_clinic"), value="clinic"),
                                    Option(_("groups.type_health_centre"), value="health_centre"),
                                    Option(_("groups.type_lab"), value="lab"),
                                    Option(_("groups.type_engineering"), value="engineering"),
                                    name="type", cls="input"),
                                style="display:flex;flex-direction:column;")),
                        cls="form-row",
                    ),
                    cls="form-group",
                ),
                Div(
                    Div(
                        Div(Label(_("groups.country"), cls="label"),
                            Div(Input(name="country", cls="input", placeholder="HN"),
                                style="display:flex;flex-direction:column;")),
                        Div(Label(_("groups.region"), cls="label"),
                            Div(Input(name="region", cls="input", placeholder=_("groups.region_placeholder")),
                                style="display:flex;flex-direction:column;")),
                        cls="form-row",
                    ),
                    cls="form-group",
                ),
                Div(
                    Div(Label(_("groups.address"), cls="label"),
                        Div(Input(name="address", cls="input", placeholder=_("groups.address_placeholder")),
                            style="display:flex;flex-direction:column;")),
                    cls="form-group",
                ),
                Div(
                    Div(Label(_("groups.contact_email"), cls="label"),
                        Div(Input(name="contact_email", type="email", cls="input"),
                            style="display:flex;flex-direction:column;")),
                    cls="form-group",
                ),
                Div(
                    Button(_("groups.org_create_btn"), type="submit", cls="btn btn-primary btn-sm"),
                    Button(_("groups.close_btn"), type="button", cls="btn btn-secondary btn-sm",
                           onclick="document.getElementById('orgDialog').close()"),
                    style="display:flex;gap:10px;margin-top:14px;",
                ),
                method="post",
                action="/groups/add-organization",
                cls="form-group"
            ),
            style="padding:18px;max-width:420px;",
        ),
        id="orgDialog",
        style="border:none;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);",
    )


def _fac_meta(fac: dict) -> str:
    bits = []
    if fac.get("country"):
        bits.append(str(fac["country"]))
    if fac.get("region"):
        bits.append(str(fac["region"]))
    if fac.get("address"):
        bits.append(str(fac["address"]))
    if fac.get("distance_km") is not None:
        bits.append(f"{fac['distance_km']:.1f} km")
    return " · ".join(bits)


def _hs_results(results, _, search, import_url="/groups/import-healthsite"):
    if not results:
        return P(_("groups.no_results"),
                 style="color:var(--c-text-3);font-size:0.85rem;margin:10px 0 0 0;")

    rows = []
    for fac in results:
        meta = f" — {_fac_meta(fac)}"
        if fac.get("already_imported"):
            rows.append(
                Div(
                    Span("✓", style="margin-right:8px;color:var(--c-green);"),
                    Span(fac.get("name", ""), style="font-weight:600;"),
                    Span(meta, style="color:var(--c-text-3);font-size:0.8rem;"),
                    Span(_("groups.already_imported"), cls="badge badge-gray", style="margin-left:8px;"),
                    style="display:flex;align-items:center;padding:8px 10px;border-radius:8px;background:var(--c-bg-soft,#f4f4f4);margin-bottom:6px;opacity:.75;",
                )
            )
            continue
        rows.append(
            Label(
                Input(type="radio", name="sel", onchange="pickHS(this)",
                      data_osm_id=fac.get("osm_id", ""), data_osm_type=fac.get("osm_type", ""),
                      data_name=fac.get("name", ""), data_country=fac.get("country", ""),
                      data_region=fac.get("region", ""), data_address=fac.get("address", ""),
                      style="margin-right:10px;"),
                Span(fac.get("name", ""), style="font-weight:600;"),
                Span(meta, style="color:var(--c-text-3);font-size:0.8rem;"),
                style="display:flex;align-items:center;padding:8px 10px;border-radius:8px;background:var(--c-blue-lt,#eef3fc);margin-bottom:6px;cursor:pointer;",
            )
        )

    return Div(
        Div(*rows, style="margin-top:10px;max-height:min(45vh,360px);overflow-y:auto;padding-right:6px;"),
        Form(
            Input(type="hidden", name="osm_id", id="hs-osm-id"),
            Input(type="hidden", name="osm_type", id="hs-osm-type"),
            Input(type="hidden", name="name", id="hs-name"),
            Input(type="hidden", name="country", id="hs-country"),
            Input(type="hidden", name="region", id="hs-region"),
            Input(type="hidden", name="address", id="hs-address"),
            Label(_("signup.role_label"), for_="hs-role", cls="label",
                  style="display:block;margin-top:10px;"),
            Select(
                Option(_("signup.role_technician"), value="technician", selected=True),
                Option(_("signup.role_clinical"), value="clinical_staff"),
                Option(_("role.engineering_staff"), value="engineering_staff"),
                name="role", id="hs-role", cls="input"
            ),
            Button(_("groups.add_selected_btn"), type="submit", id="hs-submit", disabled=True,
                   cls="btn btn-primary btn-sm", style="margin-top:12px;"),
            method="post",
            action=import_url,
            style="margin-top:12px;",
        ),
    )


def _hs_dialog(_, results=None, search=None, error="",
               search_url="/groups/search-healthsites",
               import_url="/groups/import-healthsite",
               dialog_id="hsDialog"):
    lat = search[0] if search else ""
    lng = search[1] if search else ""
    radius = search[2] if search else "2"

    error_msg = P(error, style="color:var(--c-danger);font-size:0.85rem;margin-top:8px;") if error else ""

    return Dialog(
        Div(
            H3(_("groups.modal_hs_title"), style="margin:0 0 4px 0;font-size:1.05rem;"),
            P(_("groups.modal_hs_desc"),
              style="color:var(--c-text-3);font-size:0.8rem;margin:0 0 10px 0;"),
            Form(
                Div(
                    Div(Label(_("groups.latitude"), cls="label"),
                        Div(Input(id="hs-lat", name="lat", cls="input", value=lat, placeholder="10.0"),
                            style="display:flex;flex-direction:column;")),
                    Div(Label(_("groups.longitude"), cls="label"),
                        Div(Input(id="hs-lng", name="lng", cls="input", value=lng, placeholder="-70.0"),
                            style="display:flex;flex-direction:column;")),
                    Div(Label(_("groups.radius"), cls="label"),
                        Div(Input(name="radius_km", cls="input", value=radius, style="max-width:100px;"),
                            style="display:flex;flex-direction:column;")),
                    cls="hs-grid",
                ),
                Div(
                    Button(_("groups.get_location_btn"), type="button", cls="btn btn-secondary btn-sm",
                           onclick="fillLocation()"),
                    Button("🔍 " + _("groups.scan_btn"), type="submit", id="hs-scan-btn",
                           cls="btn btn-primary btn-sm"),
                    style="display:flex;gap:10px;margin-top:14px;",
                ),
                method="post",
                action=search_url,
                id="hs-search-form",
            ),
            Div(
                Div(cls="spinner"),
                Span(_("groups.searching")),
                id="hs-loading",
                style="display:none;align-items:center;gap:10px;margin-top:12px;padding:10px 12px;"
                      "border-radius:8px;background:var(--c-blue-lt,#eef3fc);color:var(--c-primary);"
                      "font-size:0.85rem;font-weight:500;",
            ),
            error_msg,
            Div(H5(_("groups.results_heading"), style="margin:14px 0 0 0;font-size:0.9rem;")
                if results is not None else ""),
            _hs_results(results, _, search, import_url=import_url) if results is not None else "",
            Div(
                Button(_("groups.close_btn"), type="button", cls="btn btn-secondary btn-sm",
                       onclick="document.getElementById('" + dialog_id + "').close()"),
                style="margin-top:14px;",
            ),
            style="padding:18px;max-width:520px;width:90%;",
        ),
        id=dialog_id,
        style="border:none;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);",
    )


def _action_buttons(_):
    return Div(
        Button("＋ " + _("groups.add_org_btn"), cls="btn btn-primary",
               onclick="document.getElementById('orgDialog').showModal()"),
        Button("＋ " + _("groups.add_healthsite_btn"), cls="btn btn-secondary",
               onclick="document.getElementById('hsDialog').showModal()"),
        style="display:flex;gap:10px;flex-wrap:wrap;",
    )


async def _build_page(req, token, lang, orgs, *, results=None, search=None, error="", open_hs=False):
    _ = make_t(lang)

    if not orgs:
        body = Div(
            Div("🏥", style="width:56px;height:56px;background:var(--c-blue-lt);color:var(--c-primary);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
            P(_("groups.empty"), style="color:var(--c-text-3);font-size:0.9rem;text-align:center;"),
            Div(_action_buttons(_), style="margin-top:16px;display:flex;justify-content:center;"),
            style="text-align:center;padding:40px 24px;"
        )
    else:
        default_org = next((o for o in orgs if o.get("role") == "admin"), None) or orgs[0]
        other_orgs = [o for o in orgs if o.get("id") != default_org.get("id")]

        sections = [
            Div(
                H2(_("groups.default_heading"), style="margin:8px 0 8px 0;font-size:1rem;color:var(--c-text-3);"),
                _org_card(default_org, _),
            )
        ]
        if other_orgs:
            sections.append(
                Div(
                    H2(_("groups.other_heading"), style="margin:0 0 8px 0;font-size:1rem;color:var(--c-text-3);"),
                    Div(*[_org_card(o, _) for o in other_orgs],
                        style="display:flex;flex-direction:column;gap:12px;"),
                )
            )

        body = Div(
            _flash(req),
            *sections,
            style="display:flex;flex-direction:column;gap:14px;max-width:760px;",
        )

    scripts = [Script(GEOLOC_JS)]
    if open_hs:
        scripts.append(Script("document.getElementById('hsDialog') && document.getElementById('hsDialog').showModal();"))

    content = Div(
        Div(
            Div(H1(_("groups.heading")), cls="page-header"),
            _action_buttons(_),
            style="display:flex;flex-direction:column;gap:10px;",
        ),
        body,
        _org_dialog(_),
        _hs_dialog(_, results=results, search=search, error=error),
        *scripts,
    )
    return page_shell(content, current="/groups", title=_("title.groups"), lang=lang)


@rt("/groups")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")

    try:
        await _get_me_data(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
    except Exception:
        pass

    try:
        orgs = await groups_api.get_my_organizations(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        orgs = []
    except Exception:
        orgs = []

    return await _build_page(req, token, lang, orgs)


@rt("/groups/add-organization")
async def post(req, name: str = "", type: str = "hospital", country: str = "",
               region: str = "", address: str = "", contact_email: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    data = {"name": name.strip(), "country": country.strip(), "type": type}
    if region.strip():
        data["region"] = region.strip()
    if address.strip():
        data["address"] = address.strip()
    if contact_email.strip():
        data["contact_email"] = contact_email.strip()
    try:
        await groups_api.create_healthsite(token, data)
    except Exception:
        import logging
        logging.getLogger("groups.create_healthsite").exception(
            "failed to create healthsite %r", data.get("name")
        )
    return RedirectResponse("/groups", status_code=302)


@rt("/groups/search-healthsites")
async def post(req, lat: str = "", lng: str = "", radius_km: str = "20"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        lat_f = float(lat or 0)
        lng_f = float(lng or 0)
        radius_f = min(max(float(radius_km or 0), 0.1), 2.0)
    except ValueError:
        return RedirectResponse("/groups", status_code=302)

    if not lat_f or not lng_f:
        return RedirectResponse("/groups", status_code=302)

    try:
        orgs = await groups_api.get_my_organizations(token)
    except Exception:
        orgs = []

    search = (lat_f, lng_f, radius_f)
    try:
        data = await groups_api.search_healthsites(token, {
            "lat": lat_f, "lng": lng_f, "radius_km": radius_f,
        })
        return await _build_page(req, token, lang, orgs,
                                 results=data.get("facilities", []),
                                 search=search, open_hs=True)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            err = _("groups.import_nokey")
        elif e.response.status_code == 502:
            err = _("groups.import_fail")
        else:
            err = _("groups.import_fail")
    except Exception:
        err = _("groups.import_fail")
    return await _build_page(req, token, lang, orgs, search=search, error=err, open_hs=True)


@rt("/groups/import-healthsite")
async def post(req, osm_id: str = "", osm_type: str = "", name: str = "",
               country: str = "", region: str = "", address: str = "",
               role: str = "technician"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

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
        return RedirectResponse("/groups", status_code=302)

    try:
        result = await groups_api.import_healthsite(token, facility, role=role)
        if result.get("added"):
            return RedirectResponse(f"/groups?flash={_('groups.import_added')}&ok=1", status_code=302)
        return RedirectResponse(f"/groups?flash={_('groups.import_dup')}", status_code=302)
    except Exception:
        pass
    return RedirectResponse(f"/groups?flash={_('groups.import_fail')}", status_code=302)


async def _get_me_data(token: str):
    from config.api import _get
    return await _get("/api/auth/me", token)
