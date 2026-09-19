from fasthtml.common import *
from starlette.responses import RedirectResponse
import httpx

import features.auth.helper as auth_helper
import features.groups.api as groups_api
from components import page_shell
from i18n import t as make_t

rt = APIRouter()


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


@rt("/groups/{org_id}/view")
async def view_organization(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    org, redirect = await _get_member_organization(req, token, org_id)
    if redirect:
        return redirect
    if not org:
        return RedirectResponse("/groups", status_code=302)

    info_rows = [
        (_("groups.name"), org.get("name", "")),
        (_("groups.type"), _(f"groups.type_{org.get('type', 'hospital')}")),
        (_("groups.country"), org.get("country", "") or _("common.fallback")),
        (_("groups.region"), org.get("region", "") or _("common.fallback")),
    ]
    contact_email = (
        A(org["contact_email"], href=f"mailto:{org['contact_email']}",
          style="color:var(--c-primary);text-decoration:none;")
        if org.get("contact_email") else _("common.fallback")
    )

    content = Div(
        A(_("groups.back_to_groups"), href="/groups",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:inline-block;margin-bottom:16px;"),
        H1(org.get("name", "")),
        Div(
            Div(
                H3(_("groups.basic_info"), style="margin-bottom:12px;"),
                Dl(*[
                    Div(Dt(label, style="color:var(--c-text-3);font-weight:500;"), Dd(value),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;gap:16px;")
                    for label, value in info_rows
                ]),
                cls="card",
            ),
            Div(
                H3(_("groups.contact"), style="margin-bottom:12px;"),
                Dl(
                    Div(Dt(_("groups.address"), style="color:var(--c-text-3);font-weight:500;"),
                        Dd(org.get("address", "") or _("common.fallback")),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;gap:16px;"),
                    Div(Dt(_("groups.contact_email"), style="color:var(--c-text-3);font-weight:500;"),
                        Dd(contact_email),
                        style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--c-border);font-size:0.875rem;gap:16px;"),    
                ),
                cls="card",
            ),
            cls="two-col", style="margin-top:16px;",
        ),
    )
    return page_shell(content, current="/groups", title=org.get("name", ""), lang=lang)
