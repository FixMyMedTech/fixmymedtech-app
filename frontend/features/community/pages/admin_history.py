# /community/admin/history — every community change, newest first: roles
# granted or removed, status changes, applicant decisions. Needs the
# view_role_history permission (Community team).

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import admin_tabs, fmt_dt
from features.community.pages.admin_members import history_line
from i18n import t as make_t

rt = APIRouter()

PAGE = 100


@rt("/community/admin/history")
async def get(req, offset: int = 0):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    offset = max(0, offset)
    try:
        data = await community_api.history(token, offset=offset)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return RedirectResponse("/community", status_code=302)
        data = {"items": []}
    try:
        roles_by_key = {r["key"]: r for r in (await community_api.get_tree()).get("roles") or []}
    except Exception:
        roles_by_key = {}
    items = data.get("items") or []

    rows = [Tr(
        Td(fmt_dt(c.get("created_at")), style="white-space:nowrap;"),
        Td(c.get("actor_name") or Span(_("cj.admin.system"), cls="cj-small")),
        Td(A(c["target_name"], href=f"/community/admin/members?sel={c['target']}") if c.get("target_name")
           else (c.get("target") or "—")),
        Td(history_line(c, roles_by_key, lang, _)),
        Td(c.get("reason") or ""),
    ) for c in items]

    pager = Div(
        A(_("cj.admin.prev"), href=f"?offset={max(0, offset - PAGE)}", cls="btn btn-secondary btn-sm") if offset else "",
        A(_("cj.admin.next"), href=f"?offset={offset + PAGE}", cls="btn btn-secondary btn-sm")
        if len(items) >= PAGE else "",
        cls="cj-row",
    )

    content = Div(
        Div(H1(_("cj.admin.title")), cls="cj-between"),
        admin_tabs("history", req, _),
        H2(_("cj.admin.tab_history")),
        Div(Table(
            Thead(Tr(*[Th(_(k), scope="col") for k in (
                "cj.admin.col_when", "cj.admin.col_who", "cj.admin.col_member", "cj.admin.col_change",
                "cj.admin.reason")])),
            Tbody(*rows), cls="cj-table"), cls="cj-tablewrap") if rows else P(_("cj.admin.no_history")),
        pager,
        cls="cj",
    )
    return page_shell(content, current="/community/admin", title=_("cj.title.admin"), lang=lang)
