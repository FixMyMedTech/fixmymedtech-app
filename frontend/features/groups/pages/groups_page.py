from fasthtml.common import *
from starlette.responses import RedirectResponse
import features.groups.api as groups_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell, status_badge

rt = APIRouter()


@rt("/groups")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me_raw = await _get_me_data(token)
    except Exception:
        me_raw = {}

    try:
        orgs = await groups_api.get_my_organizations(token)
    except Exception:
        orgs = []

    is_admin = any(
        m.get("role") == "admin"
        for m in me_raw.get("organizations", [])
    )

    org_cards = []
    for org in orgs:
        org_id = str(org.get("id", ""))
        my_role = next(
            (m["role"] for m in me_raw.get("organizations", [])
             if str(m.get("id")) == org_id),
            ""
        )

        edit_form = Form(
            Div(
                Label(_("groups.name"), cls="label", for_=f"org-name-{org_id}"),
                Input(id=f"org-name-{org_id}", name="name",
                      value=org.get("name", ""), cls="input"),
                cls="form-group",
            ),
            Div(
                Label(_("groups.country"), cls="label", for_=f"org-country-{org_id}"),
                Input(id=f"org-country-{org_id}", name="country",
                      value=org.get("country", ""), cls="input"),
                cls="form-group",
            ),
            Button(_("groups.save"), type="submit", cls="btn btn-primary btn-sm",
                   style="margin-top:8px;"),
            method="post",
            action=f"/groups/{org_id}/edit",
            style="margin-top:12px;",
        ) if my_role == "admin" else ""

        org_cards.append(
            Div(
                Div(
                    H3(org.get("name", ""), style="margin:0 0 4px 0;font-size:1.1rem;"),
                    P(f"{_('groups.country')}: {org.get('country', '') or '—'}",
                      style="color:var(--c-text-3);font-size:0.85rem;margin:0;"),
                    style="flex:1;min-width:0;",
                ),
                Div(
                    status_badge(my_role, "fault") if my_role else "",
                    style="flex-shrink:0;margin-left:12px;",
                ),
                edit_form,
                style="display:flex;flex-wrap:wrap;align-items:flex-start;gap:12px;",
                cls="card",
            )
        )

    if not org_cards:
        body = Div(
            Div("👥", style="width:56px;height:56px;background:var(--c-blue-lt);color:var(--c-primary);border-radius:50%;font-size:1.4rem;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;"),
            P(_("groups.empty"), style="color:var(--c-text-3);font-size:0.9rem;text-align:center;"),
            style="text-align:center;padding:60px 24px;"
        )
    else:
        body = Div(*org_cards, style="display:flex;flex-direction:column;gap:14px;max-width:720px;")

    content = Div(
        Div(H1(_("groups.heading")), cls="page-header"),
        body,
    )
    return page_shell(content, current="/groups", title=_("title.groups"), lang=lang)


@rt("/groups/{org_id}/edit")
async def post(req, org_id: str, name: str = "", country: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    try:
        await groups_api.update_organization(token, org_id, {
            "name": name.strip(),
            "country": country.strip(),
        })
    except Exception:
        pass

    return RedirectResponse("/groups", status_code=302)


async def _get_me_data(token: str):
    from config.api import _get
    return await _get("/api/auth/me", token)
