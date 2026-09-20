from typing import Optional
import json

from fasthtml.common import *
from starlette.responses import RedirectResponse
import httpx

import features.auth.helper as auth_helper
import features.groups.api as groups_api
from components import page_shell
from i18n import t as make_t

rt = APIRouter()

ORG_TYPES = ("hospital", "clinic", "health_centre", "lab", "engineering")

EDIT_ORG_JS = """
function toggleOrgCard(id) {
  var display = document.getElementById(id + '-display');
  var edit = document.getElementById(id + '-edit');
  var editing = edit.style.display !== 'none';
  display.style.display = editing ? '' : 'none';
  edit.style.display = editing ? 'none' : 'block';
}
"""


def _edit_button(card_id, _):
    return Button(_("groups.edit"), type="button", cls="btn btn-secondary btn-sm",
                  onclick=f"toggleOrgCard('{card_id}')")


def _edit_row(label, control):
    return Div(Dt(label), Dd(control), cls="info-row")


def _basic_card(org: dict, _):
    card_id = "basic-info"
    display = Div(
        Dl(
            Div(Dt(_("groups.name")), Dd(org.get("name", "")), cls="info-row"),
            Div(Dt(_("groups.type")), Dd(_(f"groups.type_{org.get('type', 'hospital')}")), cls="info-row"),
            Div(Dt(_("groups.country")), Dd(org.get("country", "") or _("common.fallback")), cls="info-row"),
            Div(Dt(_("groups.region")), Dd(org.get("region", "") or _("common.fallback")), cls="info-row"),
            cls="info-list",
        ),
        id=f"{card_id}-display",
    )
    edit = Form(
        Dl(
            _edit_row(_("groups.name"), Input(name="name", value=org.get("name", ""), cls="input", style="max-width:260px;")),
            _edit_row(_("groups.type"), Select(
                *[Option(_(f"groups.type_{value}"), value=value, selected=(org.get("type") == value))
                  for value in ORG_TYPES], name="type", cls="input", style="max-width:260px;")),
            _edit_row(_("groups.country"), Input(name="country", value=org.get("country", ""), cls="input", style="max-width:260px;")),
            _edit_row(_("groups.region"), Input(name="region", value=org.get("region", "") or "", cls="input", style="max-width:260px;")),
            cls="info-list",
        ),
        Button(_("groups.save"), type="submit", cls="btn btn-primary btn-sm"),
        Button(_("groups.cancel"), type="button", cls="btn btn-secondary btn-sm",
               onclick=f"toggleOrgCard('{card_id}')"),
        method="post", action=f"/groups/{org['id']}/edit",
        id=f"{card_id}-edit", style="display:none;",
    )
    return Div(
        Div(H3(_("groups.basic_info"), style="margin:0;"), _edit_button(card_id, _),
            style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"),
        display, edit, cls="card",
    )


def _contact_card(org: dict, _):
    card_id = "contact-info"
    email = org.get("contact_email", "")
    display = Div(
        Dl(
            Div(Dt(_("groups.address")), Dd(org.get("address", "") or _("common.fallback")), cls="info-row"),
            Div(Dt(_("groups.contact_email")), Dd(email or _("common.fallback")), cls="info-row"),
            cls="info-list",
        ),
        id=f"{card_id}-display",
    )
    edit = Form(
        Dl(
            _edit_row(_("groups.address"), Input(name="address", value=org.get("address", "") or "", cls="input", style="max-width:260px;")),
            _edit_row(_("groups.contact_email"), Input(name="contact_email", type="email", value=email, cls="input", style="max-width:260px;")),
            cls="info-list",
        ),
        Button(_("groups.save"), type="submit", cls="btn btn-primary btn-sm"),
        Button(_("groups.cancel"), type="button", cls="btn btn-secondary btn-sm",
               onclick=f"toggleOrgCard('{card_id}')"),
        method="post", action=f"/groups/{org['id']}/edit",
        id=f"{card_id}-edit", style="display:none;",
    )
    return Div(
        Div(H3(_("groups.contact"), style="margin:0;"), _edit_button(card_id, _),
            style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"),
        display, edit, cls="card",
    )


def _member_manage_js(org_id):
    return """
let amDebounceTimer = null;

let amDebounce = null;
function amOnInput(orgId) {
  clearTimeout(amDebounce);
  amDebounce = setTimeout(() => searchOrgProfiles(orgId), 250);
}

async function searchOrgProfiles(orgId) {
  const q = document.getElementById('am-search').value;
  const list = document.getElementById('am-results');
  const msg = document.getElementById('am-msg');
  list.innerHTML = '';
  msg.style.display = 'none';
  if (!q.trim()) return;
  msg.innerHTML = 'Searching…';
  msg.style.display = 'block';
  try {
    const res = await fetch('/groups/' + orgId + '/search?q=' + encodeURIComponent(q), {headers:{'Accept':'application/json'}});
    const data = await res.json();
    msg.style.display = 'none';
    if (data.error) { msg.innerHTML = data.error; msg.style.display = 'block'; return; }
    if (!data.length) {
      list.innerHTML = '<div style="text-align:center;padding:16px;color:var(--c-text-3);">No profiles found.</div>';
      return;
    }
    const rows = data.map((p) => {
      const name = p.full_name || p.username || '';
      const username = p.username || p.email || '';
      return '<div class="card" style="display:flex;align-items:center;gap:12px;padding:10px 12px;margin-bottom:8px;">' +
        '<div style="font-size:0.875rem;flex:1;min-width:0;">' + name +
        (username ? ' <span style="color:var(--c-text-3);">(' + username + ')</span>' : '') + '</div>' +
        '<a class="btn btn-primary btn-sm" href="/groups/' + orgId + '/members/' + p.id + '/add">Add</a>' +
        '</div>';
    }).join('');
    list.innerHTML = rows;
  } catch (e) {
    msg.innerHTML = 'Error searching.';
    msg.style.display = 'block';
  }
}
"""


def _add_member_dialog(org, _, org_id):
    return Dialog(
        Div(
            H3(_("groups.add_member_title"), style="margin:0 0 4px 0;font-size:1.05rem;"),
            P(_("groups.add_member_desc"),
              style="color:var(--c-text-3);font-size:0.8rem;margin:0 0 12px 0;"),
            Div(
                Input(id="am-search", name="q", cls="input",
                      placeholder=_("groups.search_placeholder"), style="flex:1;",
                      oninput=f"amOnInput('{org_id}')"),
                Button(_("groups.search"), type="button", cls="btn btn-primary",
                       onclick=f"searchOrgProfiles('{org_id}')"),
                style="display:flex;gap:8px;",
            ),
            Span(_("groups.search_no_results"), id="am-msg", style="display:none;color:var(--c-text-3);font-size:0.85rem;margin-top:8px;"),
            Div(id="am-results", style="margin-top:12px;"),
            Div(
                Button(_("groups.close"), type="button", cls="btn btn-secondary btn-sm",
                       onclick="document.getElementById('amDialog').close()"),
                style="text-align:right;margin-top:12px;",
            ),
            style="padding:18px;max-width:480px;width:90%;",
        ),
        id="amDialog",
        style="border:none;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);",
    )


async def _get_member_organization(req, token, org_id):
    try:
        orgs = await groups_api.get_my_organizations(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return None, RedirectResponse("/login?expired=1", status_code=302)
        orgs = []
    except Exception:
        orgs = []
    return next((o for o in orgs if str(o.get("id")) == str(org_id)), None), None


@rt("/groups/{org_id}")
async def get_organization(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    org, redirect = await _get_member_organization(req, token, org_id)
    if redirect:
        return redirect
    if not org or org.get("role") != "admin":
        return RedirectResponse("/groups", status_code=302)

    try:
        members = await groups_api.get_organization_members(token, org_id)
    except Exception:
        members = []
    member_rows = [
        Tr(
            Td(member.get("name", ""), style="font-size:0.875rem;"),
            Td(member.get("email", ""), style="font-size:0.875rem;"),
            Td(Form(
                Select(
                    Option(_("signup.role_admin"), value="admin", selected=member.get("role") == "admin"),
                    Option(_("signup.role_technician"), value="technician", selected=member.get("role") == "technician"),
                    Option(_("signup.role_clinical"), value="clinical_staff", selected=member.get("role") == "clinical_staff"),
                    Option(_("role.engineering_staff"), value="engineering_staff", selected=member.get("role") == "engineering_staff"),
                    name="role", cls="input", onchange="this.form.submit()",
                    style="max-width:180px;padding:5px 8px;",
                ),
                method="post",
                action=f"/groups/{org_id}/members/{member['id']}/role",
            )),
            Td(Form(
                Button(_("groups.kick_out"), type="submit", cls="btn btn-danger btn-sm"),
                method="post",
                action=f"/groups/{org_id}/members/{member['id']}/remove",
                onsubmit="return confirm('Remove this user from the organization?');",
            )),
        )
        for member in members
    ]
    members_table = Table(
        Thead(Tr(
            Th(_("groups.member_name")),
            Th(_("groups.member_email")),
            Th(_("groups.member_role")),
            Th(_("groups.member_action")),
        )),
        Tbody(*member_rows) if member_rows else Tbody(
            Tr(Td(_("groups.no_members"), colspan="4",
                  style="text-align:center;padding:20px;color:var(--c-text-3);"))
        ),
    )

    content = Div(
        Script(EDIT_ORG_JS),
        Script(_member_manage_js(org_id)),
        A(_("groups.back_to_groups"), href="/groups",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:inline-block;margin-bottom:16px;"),
        H1(org.get("name", "")),
        P(_("groups.manage_desc"), style="color:var(--c-text-3);margin-bottom:18px;"),
        Div(_basic_card(org, _), _contact_card(org, _),
            cls="two-col", style="max-width:960px;margin-top:16px;"),
        Div(
            Div(
                H3(_("groups.members"), style="margin:0;"),
                Button(_("groups.add_user_btn"), type="button", cls="btn btn-primary btn-sm",
                       onclick="document.getElementById('amDialog').showModal()"),
                style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;",
            ),
            Div(members_table, cls="table-wrap"),
            cls="card", style="max-width:960px;margin-top:16px;",
        ),
        _add_member_dialog(org, _, org_id),
    )
    return page_shell(content, current="/groups", title=org.get("name", ""), lang=lang)


@rt("/groups/{org_id}/edit")
async def post(req, org_id: str, name: Optional[str] = None, type: Optional[str] = None,
               country: Optional[str] = None, region: Optional[str] = None,
               address: Optional[str] = None, contact_email: Optional[str] = None):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    data = {}
    if name is not None:
        data["name"] = name.strip()
    if type in ORG_TYPES:
        data["type"] = type
    if country is not None:
        data["country"] = country.strip()
    if region is not None:
        data["region"] = region.strip()
    if address is not None:
        data["address"] = address.strip()
    if contact_email is not None:
        data["contact_email"] = contact_email.strip()
    try:
        await groups_api.update_organization(token, org_id, data)
    except Exception:
        pass
    return RedirectResponse(f"/groups/{org_id}", status_code=303)


@rt("/groups/{org_id}/members/{member_id}/remove")
async def remove_member(req, org_id: str, member_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await groups_api.remove_organization_member(token, org_id, member_id)
    except Exception:
        pass
    return RedirectResponse(f"/groups/{org_id}", status_code=303)


@rt("/groups/{org_id}/members/{member_id}/role")
async def update_member_role(req, org_id: str, member_id: str, role: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    if role in ("admin", "technician", "clinical_staff", "engineering_staff"):
        try:
            await groups_api.update_organization_member(token, org_id, member_id, role)
        except Exception:
            pass
    return RedirectResponse(f"/groups/{org_id}", status_code=303)


@rt("/groups/{org_id}/leave")
async def leave_group(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await groups_api.leave_organization(token, org_id)
    except Exception:
        pass
    return RedirectResponse("/groups", status_code=303)


@rt("/groups/{org_id}/delete")
async def delete_group(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        await groups_api.delete_organization(token, org_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            return page_shell(
                Script(f"alert({json.dumps(_('groups.delete_has_devices'))}); window.location='/groups';"),
                current="/groups", lang=lang,
            )
    except Exception:
        pass
    return RedirectResponse("/groups", status_code=303)


@rt("/groups/{org_id}/search")
async def search_org_profiles(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    q = req.query_params.get("q", "")
    try:
        profiles = await groups_api.search_profiles(token, org_id, q)
    except Exception:
        profiles = []
    return JSONResponse([p for p in profiles if p.get("id")])


@rt("/groups/{org_id}/members/{profile_id}/add")
async def add_member(req, org_id: str, profile_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await groups_api.add_organization_member(
            token, org_id, {"profile_id": profile_id, "role": "technician"},
        )
    except Exception:
        pass
    return RedirectResponse(f"/groups/{org_id}", status_code=303)
