# /community/admin/roles — read-only view of the role catalogue: each role,
# how it unlocks, and which permissions it carries. Phase 1 edits the
# catalogue in SQLAdmin (/admin → Community roles); an editor here is phase 1b.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import admin_tabs, role_name, requirement_label, flash
from i18n import t as make_t

rt = APIRouter()

PATHS = ("start", "devices", "people", "trust", "knowledge", "teams", "parts", "leads")


@rt("/community/admin/roles")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        permissions = await community_api.list_permissions(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return RedirectResponse("/community", status_code=302)
        permissions = []
    except Exception:
        permissions = []
    try:
        tree = await community_api.get_tree()
    except Exception:
        tree = {"roles": []}
    roles = sorted(tree.get("roles") or [], key=lambda r: (PATHS.index(r["path"]) if r["path"] in PATHS else 99,
                                                           r["tier"], r["sort"]))
    roles_by_key = {r["key"]: r for r in roles}

    role_rows = [Tr(
        Td(A(role_name(r, lang), href=f"/community/roles/{r['key']}", style="font-weight:500;"),
           Div(Span(r["key"], cls="cj-small", style="font-family:var(--font-mono-ds);"))),
        Td(_(f"cj.path.{r['path']}") + " · " + _("cj.tier").format(n=r["tier"])),
        Td(_(f"cj.unlock.{r['unlock']}")),
        Td(_(f"cj.scope.{r['scope']}")),
        Td(Ul(*[Li(requirement_label(q, roles_by_key, _, lang)) for q in r.get("requirements") or []],
              style="margin:0;padding-left:16px;") if r.get("requirements") else "—"),
        Td(", ".join(r.get("permissions") or []) or "—", style="font-family:var(--font-mono-ds);font-size:12px;"),
        Td(str(r.get("holders", 0)), cls="n"),
    ) for r in roles]

    perm_rows = [Tr(
        Td(Span(p["key"], style="font-family:var(--font-mono-ds);font-size:12px;")),
        Td(_(f"cj.perm.{p['key']}", p["en"])),
        Td(_(f"cj.perm_group.{p['group']}", p["group"])),
        Td(", ".join(role_name(roles_by_key.get(k, {"key": k}), lang) for k in p.get("roles") or []) or "—"),
    ) for p in permissions]

    content = Div(
        Div(H1(_("cj.admin.title")), cls="cj-between"),
        admin_tabs("roles", req, _),
        flash(_("cj.admin.roles_edit_note"), "info"),
        H2(_("cj.admin.tab_roles")),
        Div(Table(
            Thead(Tr(*[Th(_(k), scope="col", cls="n" if k == "cj.admin.col_holders" else None) for k in (
                "cj.admin.role", "cj.admin.col_path", "cj.admin.col_unlock", "cj.admin.col_scope",
                "cj.admin.col_requirements", "cj.admin.col_permissions", "cj.admin.col_holders")])),
            Tbody(*role_rows), cls="cj-table"), cls="cj-tablewrap"),
        H2(_("cj.admin.permissions_title")) if perm_rows else "",
        P(_("cj.admin.permissions_text")) if perm_rows else "",
        Div(Table(
            Thead(Tr(*[Th(_(k), scope="col") for k in (
                "cj.admin.col_key", "cj.admin.col_what", "cj.admin.col_group", "cj.admin.col_roles")])),
            Tbody(*perm_rows), cls="cj-table"), cls="cj-tablewrap") if perm_rows else "",
        cls="cj",
    )
    return page_shell(content, current="/community/admin", title=_("cj.title.admin"), lang=lang)
