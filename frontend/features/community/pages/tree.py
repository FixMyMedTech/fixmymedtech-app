# /community/tree — the skill tree. Public: visitors see the roles they could
# grow into; members also see which they hold and which are open now.

from fasthtml.common import *

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell, pub_shell
from features.community.ui import role_name, flash
from i18n import t as make_t

rt = APIRouter()

PATHS = ("start", "devices", "people", "trust", "knowledge", "teams", "parts", "leads")


def node_state(role: dict, progress: dict | None) -> str:
    """held, open (its role prerequisites are held) or locked."""
    if progress is None:
        return ""
    state = progress.get(role["key"]) or {}
    if state.get("held"):
        return "held"
    roles_ok = all(r.get("met") for r in state.get("requirements", []) if r.get("kind") == "role")
    if roles_ok and role.get("unlock") != "assigned":
        return "open"
    return "locked"


def tree_grid(tree: dict, progress: dict | None, _, lang: str):
    roles = tree.get("roles") or []
    cols = []
    for path in PATHS:
        in_path = sorted([r for r in roles if r["path"] == path], key=lambda r: (r["tier"], r["sort"]))
        if not in_path:
            continue
        nodes = []
        for r in in_path:
            state = node_state(r, progress)
            meta = [_("cj.tier").format(n=r["tier"]), _(f"cj.unlock.{r['unlock']}")]
            if state:
                meta.append(_(f"cj.state.{state}"))
            nodes.append(A(
                Span(role_name(r, lang), cls="cj-node-name"),
                Span(" · ".join(meta), cls="cj-node-meta"),
                Span(_("cj.holders").format(n=r.get("holders", 0)), cls="cj-node-meta"),
                href=f"/community/roles/{r['key']}",
                cls=f"cj-node {state}".strip(),
            ))
        cols.append(Div(Div(_(f"cj.path.{path}"), cls="cj-path-title"), *nodes, cls="cj-path"))
    return Div(*cols, cls="cj-tree")


@rt("/community/tree")
async def get(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    token = auth_helper.get_token(req)
    try:
        tree = await community_api.get_tree()
    except Exception:
        tree = {"roles": []}
    progress = None
    if token:
        try:
            progress = (await community_api.get_me(token)).get("progress")
        except Exception:
            progress = None

    content = Div(
        Div(H1(_("cj.tree.title")), P(_("cj.tree.intro")), cls="cj-card"),
        Div(
            Span(_("cj.state.held"), cls="badge badge-ok"),
            Span(_("cj.state.open"), cls="badge badge-warn"),
            Span(_("cj.state.locked"), cls="badge badge-neutral"),
            Span(_("cj.tree.legend"), cls="cj-small"),
            cls="cj-row",
        ) if progress is not None else "",
        tree_grid(tree, progress, _, lang) if tree.get("roles") else flash(_("cj.error.load"), "error"),
        Div(
            P(_("cj.tree.join_text")),
            A(_("cj.tree.join_button"), href="/join", cls="btn btn-primary", style="align-self:flex-start;"),
            cls="cj-card",
        ) if not token else "",
        cls="cj",
    )
    shell = page_shell if token else pub_shell
    return shell(content, current="/community/tree", title=_("cj.title.tree"), lang=lang) if token \
        else shell(content, title=_("cj.title.tree"), lang=lang)
