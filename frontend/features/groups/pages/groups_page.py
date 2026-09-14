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
  document.getElementById('hs-lat').value = el.dataset.lat || '';
  document.getElementById('hs-lng').value = el.dataset.lng || '';
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


def _coords_str(org: dict) -> str:
    if org.get("latitude") is not None and org.get("longitude") is not None:
        return f"· {org['latitude']:.4f}, {org['longitude']:.4f}"
    return ""


def _org_card(org: dict, _):
    org_id = str(org.get("id", ""))
    is_admin = org.get("role") == "admin"
    coords = _coords_str(org)

    edit_form = Form(
        Div(
            Div(Label(_("groups.name"), cls="label"),
                Div(Input(name="name", value=org.get("name", ""), cls="input"),
                    style="display:flex;flex-direction:column;")),
            Div(Label(_("groups.country"), cls="label"),
                Div(Input(name="country", value=org.get("country", ""), cls="input"),
                    style="display:flex;flex-direction:column;")),
            Div(Label(_("groups.latitude"), cls="label"),
                Div(Input(name="latitude", value="" if org.get("latitude") is None else org["latitude"],
                          cls="input"), style="display:flex;flex-direction:column;")),
            Div(Label(_("groups.longitude"), cls="label"),
                Div(Input(name="longitude", value="" if org.get("longitude") is None else org["longitude"],
                          cls="input"), style="display:flex;flex-direction:column;")),
            cls="hs-grid",
        ),
        Button(_("groups.save"), type="submit", cls="btn btn-primary btn-sm",
               style="margin-top:8px;"),
        method="post",
        action=f"/groups/{org_id}/edit",
        style="margin-top:12px;",
    ) if is_admin else ""

    return Div(
        Div(
            Div(
                H3(org.get("name", ""), style="margin:0 0 4px 0;font-size:1.1rem;"),
                P(f"{_('groups.country')}: {org.get('country', '') or '—'} {coords}",
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
        edit_form,
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
                    Div(Label(_("groups.name"), cls="label"),
                        Div(Input(name="name", cls="input", placeholder=_("groups.site_name_placeholder")),
                            style="display:flex;flex-direction:column;")),
                    Div(Label(_("groups.country"), cls="label"),
                        Div(Input(name="country", cls="input", placeholder="HN"),
                            style="display:flex;flex-direction:column;")),
                    Div(Label(_("groups.latitude"), cls="label"),
                        Div(Input(name="latitude", cls="input", placeholder="10.0"),
                            style="display:flex;flex-direction:column;")),
                    Div(Label(_("groups.longitude"), cls="label"),
                        Div(Input(name="longitude", cls="input", placeholder="-70.0"),
                            style="display:flex;flex-direction:column;")),
                    cls="hs-grid",
                ),
                Div(
                    Button(_("groups.org_create_btn"), type="submit", cls="btn btn-primary btn-sm"),
                    Button(_("groups.close_btn"), type="button", cls="btn btn-secondary btn-sm",
                           onclick="document.getElementById('orgDialog').close()"),
                    style="display:flex;gap:10px;margin-top:14px;",
                ),
                method="post",
                action="/groups/add-organization",
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
    if fac.get("distance_km") is not None:
        bits.append(f"{fac['distance_km']:.1f} km")
    if fac.get("lat") is not None and fac.get("lng") is not None:
        bits.append(f"{fac['lat']:.4f}, {fac['lng']:.4f}")
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
                      data_lat=fac.get("lat") or "", data_lng=fac.get("lng") or "",
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
            Input(type="hidden", name="lat", id="hs-lat"),
            Input(type="hidden", name="lng", id="hs-lng"),
            Button(_("groups.add_selected_btn"), type="submit", id="hs-submit", disabled=True,
                   cls="btn btn-primary btn-sm"),
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
                H2(_("groups.default_heading"), style="margin:0 0 8px 0;font-size:1rem;color:var(--c-text-3);"),
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


@rt("/groups/{org_id}/edit")
async def post(req, org_id: str, name: str = "", country: str = "", latitude: str = "", longitude: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    data = {
        "name": name.strip(),
        "country": country.strip(),
    }
    if latitude.strip():
        try:
            data["latitude"] = float(latitude.strip())
        except ValueError:
            pass
    if longitude.strip():
        try:
            data["longitude"] = float(longitude.strip())
        except ValueError:
            pass
    try:
        await groups_api.update_organization(token, org_id, data)
    except Exception:
        pass
    return RedirectResponse("/groups", status_code=302)


@rt("/groups/add-organization")
async def post(req, name: str = "", country: str = "", latitude: str = "", longitude: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    data = {"name": name.strip(), "country": country.strip(), "type": "hospital"}
    if latitude.strip():
        try:
            data["latitude"] = float(latitude.strip())
        except ValueError:
            pass
    if longitude.strip():
        try:
            data["longitude"] = float(longitude.strip())
        except ValueError:
            pass
    try:
        await groups_api.create_healthsite(token, data)
        return RedirectResponse("/groups", status_code=302)
    except Exception:
        pass
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
               country: str = "", lat: str = "", lng: str = ""):
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
    if lat.strip():
        try:
            facility["lat"] = float(lat.strip())
        except ValueError:
            pass
    if lng.strip():
        try:
            facility["lng"] = float(lng.strip())
        except ValueError:
            pass

    if not facility["osm_id"] or not facility["name"]:
        return RedirectResponse("/groups", status_code=302)

    try:
        result = await groups_api.import_healthsite(token, facility)
        if result.get("added"):
            return RedirectResponse(f"/groups?flash={_('groups.import_added')}&ok=1", status_code=302)
        return RedirectResponse(f"/groups?flash={_('groups.import_dup')}", status_code=302)
    except Exception:
        pass
    return RedirectResponse(f"/groups?flash={_('groups.import_fail')}", status_code=302)


async def _get_me_data(token: str):
    from config.api import _get
    return await _get("/api/auth/me", token)