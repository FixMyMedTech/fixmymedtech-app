# pages/network.py — the Network directory.
#
# Every active member of the platform, ordered by how active they are: most
# device registrations first, then repairs, then closed maintenance logs, then
# people invited. Members can override the order per column in the List view.
#
# Two presentations of the same data, switched with ?view=cards|table. The
# choice lives in the query string rather than session state so it survives a
# reload, a Load-more and a shared link. The whole card (or the member's name
# in the table) links to their public profile, carrying the current view/sort
# so returning from that page lands you back where you were.
#
# The first page is server-rendered; "Load more" pulls further pages from
# /network/more, which returns a bare Fragment of cards or rows so the markup
# is never rebuilt in JavaScript.

from urllib.parse import urlencode

from fasthtml.common import *
from starlette.responses import HTMLResponse, RedirectResponse

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.profile.api as profile_api

from components import page_shell

rt = APIRouter()

PAGE_SIZE = 24

VIEW_CARDS = "cards"
VIEW_TABLE = "table"
DEFAULT_SORT = "default"   # the composite leaderboard, when no column is picked

# The four metrics the backend sorts by, in display order. `name` is not a
# metric so it is rendered separately as the leading column.
SORT_COLS = ("devices", "repairs", "maintenance", "invites")
COL_LABELS = {
    "devices": "network.col_devices",
    "repairs": "network.col_repairs",
    "maintenance": "network.col_maintenance",
    "invites": "network.col_invites",
}

NET_JS = """
async function netMore() {
  var btn = document.getElementById('net-more');
  var grid = document.getElementById('net-grid');
  var body = document.getElementById('net-tbody');
  var host = grid || body;
  var input = document.getElementById('net-q');
  if (!btn || !host) return;
  btn.disabled = true;

  var q = ((input && input.value) || '').trim();
  var view = body ? 'table' : 'cards';
  var sort = btn.getAttribute('data-sort') || '';
  var dir = btn.getAttribute('data-dir') || '';
  var url = '/network/more?offset=' + host.children.length +
            '&view=' + view +
            '&q=' + encodeURIComponent(q) +
            '&sort=' + encodeURIComponent(sort) +
            '&dir=' + encodeURIComponent(dir);

  try {
    var r = await fetch(url);
    if (!r.ok) { btn.disabled = false; return; }
    var html = await r.text();
    var before = host.children.length;
    host.insertAdjacentHTML('beforeend', html);
    // Fewer results than a full page means we have reached the end.
    if (host.children.length - before < NET_PAGE) btn.style.display = 'none';
  } catch (e) {
    // Transient failure: leave the button enabled so it can be retried.
  }
  btn.disabled = false;
}
"""


def _role_label(role, _):
    if not role:
        return ""
    key = f"role.{role}"
    label = _(key)
    return role.replace("_", " ") if label == key else label


def _initials(p: dict) -> str:
    name = (p.get("full_name") or p.get("username") or "?").strip()
    parts = [w for w in name.split() if w][:2]
    return "".join(w[0].upper() for w in parts) or "?"


def _face(p: dict, cls="net-avatar"):
    pid = p.get("id")
    avatar_key = p.get("avatar_key") or ""
    if avatar_key:
        return Img(src=f"/profile/{pid}/photo?v={avatar_key}", alt="", cls=cls)
    return Div(_initials(p), cls=f"{cls} net-initials")


def _qs(q="", view=VIEW_CARDS, sort="", direction=""):
    """A /network querystring with defaults omitted, so a clean cards view
    stays at a bare /network and a plain switch to List stays at ?view=table.
    `dir` only matters once a column has actually been picked."""
    params = {}
    if q:
        params["q"] = q
    if view != VIEW_CARDS:
        params["view"] = view
    if sort and sort != DEFAULT_SORT:
        params["sort"] = sort
        if direction:
            params["dir"] = direction
    return f"?{urlencode(params)}" if params else ""


def _back_path(q, view, sort, direction):
    """Where a member should return to from a profile page. Carried in full so
    the view and ordering survive the round-trip."""
    return "/network" + _qs(q, view, sort, direction)


def _next_dir(active_sort, active_dir, col):
    """Clicking the active column flips it; clicking a new one starts at the
    direction that reads naturally for it (biggest first for a metric,
    A→Z for a name)."""
    if col == active_sort:
        return "asc" if active_dir == "desc" else "desc"
    return "asc" if col == "name" else "desc"


def _card(p: dict, _, back):
    pid = p.get("id")
    name = p.get("full_name") or p.get("username") or ""
    username = p.get("username") or ""
    country = p.get("country") or ""
    role = _role_label(p.get("role"), _)
    org = (p.get("organization") or {}).get("name") or ""

    return A(
        _face(p),
        Div(name, cls="net-name"),
        Div(f"@{username}" if username else "", cls="net-username"),
        Div(country, cls="net-country") if country else "",
        Div(role, cls="net-role") if role else "",
        Div(org, cls="net-org") if org else "",
        href=f"/profile/{pid}?{urlencode({'back': back})}",
        cls="net-card",
        title=name or username,
    )


def _row(p: dict, _, back):
    pid = p.get("id")
    name = p.get("full_name") or p.get("username") or ""
    username = p.get("username") or ""

    return Tr(
        Td(
            A(
                _face(p, cls="net-avatar net-avatar-sm"),
                Div(
                    Div(name, cls="net-name"),
                    Div(f"@{username}" if username else "", cls="net-username"),
                    cls="net-row-text",
                ),
                href=f"/profile/{pid}?{urlencode({'back': back})}",
                cls="net-row-link",
                title=name or username,
            ),
            cls="net-td-name",
        ),
        Td(str(p.get("devices_registered", 0)), cls="net-num"),
        Td(str(p.get("faults_resolved", 0)), cls="net-num"),
        Td(str(p.get("maintenance_performed", 0)), cls="net-num"),
        Td(str(p.get("invites", 0)), cls="net-num"),
    )


def _sort_header(col, label_key, _, q, active_sort, active_dir, extra_cls=""):
    nxt = _next_dir(active_sort, active_dir, col)
    href = "/network" + _qs(q, VIEW_TABLE, col, nxt)
    active = col == active_sort
    arrow = Span("↓" if active_dir == "desc" else "↑", cls="net-sort-ico") if active else ""
    return Th(
        A(_(label_key), arrow, href=href, cls="net-sort" + (" is-active" if active else "")),
        cls=("net-th " + extra_cls).strip(),
    )


def _table(items, _, q, active_sort, active_dir, back):
    head = Tr(
        _sort_header("name", "network.col_name", _, q, active_sort, active_dir,
                     extra_cls="net-th-name"),
        *[_sort_header(c, COL_LABELS[c], _, q, active_sort, active_dir) for c in SORT_COLS],
    )
    return Div(
        Table(
            Thead(head),
            Tbody(*[_row(p, _, back) for p in items], id="net-tbody"),
            cls="net-table",
            id="net-table",
        ),
        cls="net-table-wrap",
    )


def _view_toggle(q, view, sort, direction, _):
    def btn(value, label_key):
        active = view == value
        return A(_(label_key),
                 href="/network" + _qs(q, value, sort, direction),
                 cls="net-view-btn" + (" is-active" if active else ""),
                 aria_pressed="true" if active else "false")
    return Div(
        btn(VIEW_CARDS, "network.view_cards"),
        btn(VIEW_TABLE, "network.view_list"),
        cls="net-view",
        role="group",
        aria_label=_("network.view_cards") + " / " + _("network.view_list"),
    )


def _search_form(q, view, sort, direction, _):
    hidden = [
        Input(type="hidden", name="view", value=view),
        Input(type="hidden", name="sort", value=sort),
        Input(type="hidden", name="dir", value=direction),
    ]
    return Form(
        Input(type="search", name="q", id="net-q", value=q,
              placeholder=_("network.search_placeholder"), cls="input",
              style="max-width:320px;"),
        *hidden,
        Button(_("network.search"), type="submit", cls="btn btn-secondary"),
        method="get", action="/network",
        style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;",
    )


@rt("/network")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    title = _("network.heading")

    q = req.query_params.get("q", "")
    view = VIEW_TABLE if req.query_params.get("view") == VIEW_TABLE else VIEW_CARDS
    direction = req.query_params.get("dir") or "desc"
    sort_param = req.query_params.get("sort") or ""

    try:
        data = await profile_api.list_profiles(token, q, PAGE_SIZE, 0,
                                               sort=sort_param, direction=direction)
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", 0)
        if status == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        data = {"items": [], "total": 0}

    items = data.get("items", [])
    total = data.get("total", 0)
    # Trust the echoed values, not the raw query string: the backend is the
    # authority on what was actually applied.
    active_sort = data.get("sort") or "default"
    active_dir = data.get("dir") or direction
    back = _back_path(q, view, active_sort, active_dir)

    if not items:
        body = P(_("network.empty"),
                 style="color:var(--c-text-3);font-size:.9rem;padding:24px 0;margin:12px auto 0;")
    elif view == VIEW_TABLE:
        body = _table(items, _, q, active_sort, active_dir, back)
    else:
        body = Div(*[_card(p, _, back) for p in items], cls="net-grid", id="net-grid")

    more = (Button(_("network.load_more"), id="net-more", cls="btn btn-secondary",
                   style="display:block;margin:18px auto 0;", onclick="netMore()",
                   data_sort=active_sort if active_sort != "default" else "",
                   data_dir=active_dir)
            if total > len(items) else "")

    content = Div(
        Div(
            Div(
                H1(title),
                P(f"{total} {_('network.member' if total == 1 else 'network.members')}",
                  style="color:var(--c-text-3);margin:4px 0 0;"),
            ),
            cls="page-header",
            style="flex-direction:column;align-items:stretch;margin:18px auto 0;",
        ),
        Div(
            _search_form(q, view, active_sort, active_dir, _),
            _view_toggle(q, view, active_sort, active_dir, _),
            cls="net-toolbar",
        ),
        body,
        more,
        Script("const NET_PAGE = " + str(PAGE_SIZE) + ";\n" + NET_JS),
    )

    return page_shell(content, current="/network",
                      title=f"{title} — {_('brand')}", lang=lang)


@rt("/network/more")
async def get_more(req):
    """A bare run of cards or table rows for the Load-more button. No shell, no
    chrome — and an empty fragment on auth failure, so a fetch can never append
    a login page.

    Serialised by hand: returning an FT element from a FastHTML route makes it
    wrap the markup in the default page, which is useless to insertAdjacentHTML.
    """
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return HTMLResponse("")

    _ = make_t(req.session.get("lang", "en"))
    q = req.query_params.get("q", "")
    view = VIEW_TABLE if req.query_params.get("view") == VIEW_TABLE else VIEW_CARDS
    direction = req.query_params.get("dir") or "desc"
    sort_param = req.query_params.get("sort") or ""
    try:
        offset = int(req.query_params.get("offset", "0"))
    except ValueError:
        offset = 0

    try:
        data = await profile_api.list_profiles(token, q, PAGE_SIZE, offset,
                                               sort=sort_param, direction=direction)
    except Exception:
        return HTMLResponse("")

    items = data.get("items", [])
    active_sort = data.get("sort") or "default"
    active_dir = data.get("dir") or direction
    back = _back_path(q, view, active_sort, active_dir)

    if view == VIEW_TABLE:
        frag = Fragment(*[_row(p, _, back) for p in items])
    else:
        frag = Fragment(*[_card(p, _, back) for p in items])
    return HTMLResponse(str(frag))
