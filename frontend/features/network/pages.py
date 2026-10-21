# pages/network.py — the Network directory.
#
# Every active member of the platform as a card; the whole card links to their
# public profile (?back=network so that page returns here rather than to the
# device list). The first page is server-rendered; "Load more" pulls further
# pages from /network/more, which returns a bare Fragment of cards so the
# markup is never rebuilt in JavaScript.

from fasthtml.common import *
from starlette.responses import HTMLResponse, RedirectResponse

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.profile.api as profile_api

from components import page_shell

rt = APIRouter()

PAGE_SIZE = 24

NET_JS = """
async function netMore() {
  var btn = document.getElementById('net-more');
  var grid = document.getElementById('net-grid');
  var input = document.getElementById('net-q');
  if (!btn || !grid) return;
  btn.disabled = true;

  var q = ((input && input.value) || '').trim();
  var url = '/network/more?offset=' + grid.children.length + '&q=' + encodeURIComponent(q);

  try {
    var r = await fetch(url);
    if (!r.ok) { btn.disabled = false; return; }
    var html = await r.text();
    var before = grid.children.length;
    grid.insertAdjacentHTML('beforeend', html);
    // Fewer cards than a full page means we have reached the end.
    if (grid.children.length - before < NET_PAGE) btn.style.display = 'none';
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


def _card(p: dict, _):
    pid = p.get("id")
    avatar_key = p.get("avatar_key") or ""
    name = p.get("full_name") or p.get("username") or ""
    username = p.get("username") or ""
    country = p.get("country") or ""
    role = _role_label(p.get("role"), _)
    org = (p.get("organization") or {}).get("name") or ""

    face = (Img(src=f"/profile/{pid}/photo?v={avatar_key}", alt="", cls="net-avatar")
            if avatar_key else Div(_initials(p), cls="net-avatar net-initials"))

    return A(
        face,
        Div(name, cls="net-name"),
        Div(f"@{username}" if username else "", cls="net-username"),
        Div(country, cls="net-country") if country else "",
        Div(role, cls="net-role") if role else "",
        Div(org, cls="net-org") if org else "",
        href=f"/profile/{pid}?back=network",
        cls="net-card",
        title=name or username,
    )


def _search_form(q: str, _):
    return Form(
        Input(type="search", name="q", id="net-q", value=q,
              placeholder=_("network.search_placeholder"), cls="input",
              style="max-width:320px;"),
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

    try:
        data = await profile_api.list_profiles(token, q, PAGE_SIZE, 0)
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", 0)
        if status == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        data = {"items": [], "total": 0}

    items = data.get("items", [])
    total = data.get("total", 0)

    body = (Div(*[_card(p, _) for p in items], cls="net-grid", id="net-grid")
            if items
            else P(_("network.empty"),
                    style="color:var(--c-text-3);font-size:.9rem;padding:24px 0;margin:12px auto 0;"))

    more = (Button(_("network.load_more"), id="net-more", cls="btn btn-secondary",
                   style="display:block;margin:18px auto 0;", onclick="netMore()")
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
        _search_form(q, _),
        body,
        more,
        Script("const NET_PAGE = " + str(PAGE_SIZE) + ";\n" + NET_JS),
    )

    return page_shell(content, current="/network",
                      title=f"{title} — {_('brand')}", lang=lang)


@rt("/network/more")
async def get_more(req):
    """A bare run of cards for the Load-more button. No shell, no chrome — and
    an empty fragment on auth failure, so a fetch can never append a login page.

    Serialised by hand: returning an FT element from a FastHTML route makes it
    wrap the markup in the default page, which is useless to insertAdjacentHTML.
    """
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return HTMLResponse("")

    _ = make_t(req.session.get("lang", "en"))
    q = req.query_params.get("q", "")
    try:
        offset = int(req.query_params.get("offset", "0"))
    except ValueError:
        offset = 0

    try:
        data = await profile_api.list_profiles(token, q, PAGE_SIZE, offset)
    except Exception:
        return HTMLResponse("")

    frag = Fragment(*[_card(p, _) for p in data.get("items", [])])
    return HTMLResponse(str(frag))
