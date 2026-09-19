from typing import Optional

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


def _basic_card(org: dict, _):
    card_id = "basic-info"
    display = Div(
        Dl(
            Div(Dt(_("groups.name")), Dd(org.get("name", "")), cls="info-row"),
            Div(Dt(_("groups.type")), Dd(_(f"groups.type_{org.get('type', 'hospital')}")), cls="info-row"),
            Div(Dt(_("groups.country")), Dd(org.get("country", "") or _("common.fallback")), cls="info-row"),
            Div(Dt(_("groups.region")), Dd(org.get("region", "") or _("common.fallback")), cls="info-row"),
        ),
        id=f"{card_id}-display",
    )
    edit = Form(
        Div(
            Div(Label(_("groups.name"), cls="label"), Input(name="name", value=org.get("name", ""), cls="input")),
            Div(Label(_("groups.type"), cls="label"), Select(
                *[Option(_(f"groups.type_{value}"), value=value, selected=(org.get("type") == value))
                  for value in ORG_TYPES], name="type", cls="input")),
            Div(Label(_("groups.country"), cls="label"), Input(name="country", value=org.get("country", ""), cls="input")),
            Div(Label(_("groups.region"), cls="label"), Input(name="region", value=org.get("region", "") or "", cls="input")),
            cls="hs-grid",
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
        ),
        id=f"{card_id}-display",
    )
    edit = Form(
        Div(
            Div(Label(_("groups.address"), cls="label"), Input(name="address", value=org.get("address", "") or "", cls="input")),
            Div(Label(_("groups.contact_email"), cls="label"), Input(name="contact_email", type="email", value=email, cls="input")),
            cls="hs-grid",
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

    content = Div(
        Script(EDIT_ORG_JS),
        A(_("groups.back_to_groups"), href="/groups",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:inline-block;margin-bottom:16px;"),
        H1(org.get("name", "")),
        P(_("groups.manage_desc"), style="color:var(--c-text-3);margin-bottom:18px;"),
        Div(_basic_card(org, _), _contact_card(org, _),
            style="display:flex;flex-direction:column;gap:16px;max-width:680px;"),
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
