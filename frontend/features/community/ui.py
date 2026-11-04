# ui.py — shared pieces of the community journey pages.
#
# Every style comes from the FixMyMedTech design system tokens (the .cj-*
# classes in components.py). Team and achievement names come from the
# database (team leads edit them); every other string is in i18n.py.

import json
import re

from fasthtml.common import *
from fasthtml.svg import Svg, Polygon

import features.auth.helper as auth_helper
import features.profile.api as profile_api
from components import lucide, DASHBOARD_PERMISSIONS
from countries import COUNTRIES


def text_of(item: dict | None, field: str, lang: str) -> str:
    value = (item or {}).get(field) or {}
    return value.get(lang) or value.get("en") or ""


def name_of(item: dict | None, lang: str) -> str:
    """A team's or achievement's name in the viewer's language."""
    return text_of(item, "names", lang) or (item or {}).get("key", "")


def tasks_of(team: dict | None, lang: str) -> list[str]:
    tasks = (team or {}).get("tasks") or {}
    return tasks.get(lang) or tasks.get("en") or []


def stars(level: int, total: int = 10, cls: str = "cj-stars"):
    """Filled and empty stars, readable by screen readers as 'Level 3 of 10'."""
    return Span(*[Span("★" if i < level else "☆", cls="on" if i < level else None, aria_hidden="true")
                  for i in range(total)],
                cls=cls, role="img", aria_label=f"{level}/{total}")


def check_mark(done: bool):
    return Span(lucide("check") if done else "", cls="cj-check", aria_hidden="true")


def progress_bar(done: int, total: int, label: str = ""):
    pct = 0 if not total else round(100 * min(done, total) / total)
    return Div(Span(style=f"width:{pct}%"), cls="cj-bar", role="progressbar",
               aria_valuenow=str(done), aria_valuemin="0", aria_valuemax=str(total),
               aria_label=label or f"{done}/{total}")


def hero(title, text="", eyebrow=""):
    return Div(
        Span(eyebrow, cls="cj-eyebrow") if eyebrow else "",
        H1(title),
        P(text) if text else "",
        cls="cj-hero",
    )


def flash(msg: str, kind: str = "success"):
    return Div(msg, cls=f"alert alert-{kind}", role="status") if msg else ""


def country_select(name: str, value: str, _, required: bool = False, id: str = None):
    return Select(
        Option(_("cj.form.choose_country"), value=""),
        *[Option(c, value=c, selected=(c == value)) for c in COUNTRIES],
        name=name, id=id or name, cls="input", required=required,
    )


def has_dashboard(req) -> bool:
    return bool(set(req.session.get("community_permissions") or []) & set(DASHBOARD_PERMISSIONS))


def can(req, key: str) -> bool:
    """True when the session's community permissions include key, e.g.
    can(req, "recognise:clinics_connector")."""
    return key in perms(req)


def perms(req) -> set:
    return set(req.session.get("community_permissions") or [])


async def refresh_session(req, token: str) -> None:
    """Re-read /api/auth/me after a community change (status, teams)."""
    try:
        auth_helper.store_me(req, await profile_api.get_me(token))
    except Exception:
        pass


def error_detail(e) -> str:
    try:
        return e.response.json().get("detail") or str(e)
    except Exception:
        return str(e)


# ── YouTube intro video ──────────────────────────────────────
# Embedded with the YouTube IFrame Player API on youtube-nocookie.com. When
# the player reaches ENDED, the page posts the quest; the "I've watched it"
# button is the fallback (blocked iframes, slow connections).

_YT_ID = re.compile(r"(?:youtu\.be/|v=|/embed/|/shorts/)([A-Za-z0-9_-]{11})")


def youtube_id(url: str) -> str:
    m = _YT_ID.search(url or "")
    return m.group(1) if m else ""


def intro_video(url: str, done: bool, _, action: str = "/community/start/video"):
    vid = youtube_id(url)
    button = Form(
        Button(_("cj.video.watched_button"), type="submit", cls="btn btn-secondary btn-sm"),
        method="post", action=action, id="cj-video-form",
    ) if not done else Span(_("cj.video.done"), cls="badge badge-ok")
    if not vid:
        return Div(P(_("cj.video.missing")), button, cls="cj-row")
    script = Script(f"""
(function(){{
  var done = {json.dumps(bool(done))};
  window.onYouTubeIframeAPIReady = function(){{
    new YT.Player('cj-player', {{
      host: 'https://www.youtube-nocookie.com',
      videoId: {json.dumps(vid)},
      playerVars: {{ rel: 0, modestbranding: 1 }},
      events: {{ onStateChange: function(e){{
        if (e.data === 0 && !done) {{ done = true; var f = document.getElementById('cj-video-form'); if (f) f.submit(); }}
      }} }}
    }});
  }};
  var s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(s);
}})();
""")
    return Div(
        Div(Div(id="cj-player"), cls="cj-video"),
        Div(button, cls="cj-row"),
        script,
        cls="cj-quest-body",
    )


# ── Dashboard tabs ───────────────────────────────────────────

ADMIN_TABS = (
    ("applicants", "/community/admin/applicants", "view_applicants"),
    ("members",    "/community/admin/members",    "view_members"),
    ("teams",      "/community/admin/teams",      None),
    ("history",    "/community/admin/history",    "view_history"),
)


def admin_tabs(current: str, req, _):
    mine = perms(req)
    return Nav(
        *[A(_(f"cj.admin.tab_{key}"), href=href, cls="cj-tab" + (" on" if key == current else ""),
            aria_current="page" if key == current else None)
          for key, href, need in ADMIN_TABS if need is None or need in mine],
        cls="cj-tabs", aria_label=_("cj.admin.title"),
    )


def first_admin_tab(req) -> str | None:
    mine = perms(req)
    for key, href, need in ADMIN_TABS:
        if need and need in mine:
            return href
    return None


def fmt_dt(iso: str | None) -> str:
    if not iso:
        return ""
    return iso.replace("T", " ")[:16]


# ── Achievements map (hexagon tiles) ─────────────────────────
# Flat-top hexagons on an "odd-q" grid: odd columns sit half a tile lower.
# Each tile is a link; its shape is an SVG polygon so the border can be
# solid (done, can do now) or dashed (what comes after). Fog tiles are
# decoration: what the community hasn't discovered yet.

HEX_POINTS = "25,1 75,1 99,43.3 75,85.6 25,85.6 1,43.3"
MAP_COLS, MAP_ROWS = 5, 5

# (col, row) of each tile. Keys: "member", "team:<key>", "ach:<key>", or None for fog.
MAP_LAYOUT = {
    (0, 2): "member",
    (1, 1): "team:communicator",
    (1, 2): "team:community_builder",
    (1, 3): "team:clinics_connector",
    (2, 2): "ach:supporter",
    (2, 3): "ach:event_organiser",
    (3, 2): "ach:active_builder",
    (2, 4): "ach:mapper",
    (1, 4): "ach:ambassador",
}
FOG = [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 1), (4, 2), (3, 3), (4, 3), (3, 4)]


def hex_map(tiles: dict, selected: str, href, label: str):
    """tiles: {key: {"name", "sub", "state", "level"}} for keys in MAP_LAYOUT.
    state is done | now | next (or "" when nobody is signed in)."""
    w = 100 / (0.75 * (MAP_COLS - 1) + 1)          # tile width, % of map width
    h_ratio = 0.866                                 # tile height / width
    map_h = (MAP_ROWS + 0.5) * h_ratio * w          # map height in the same units
    def box(col, row):
        top = (row + (0.5 if col % 2 else 0)) * h_ratio * w
        return f"left:{col * 0.75 * w:.3f}%;top:{100 * top / map_h:.3f}%;width:{w:.3f}%;height:{100 * h_ratio * w / map_h:.3f}%"
    items = []
    for pos in FOG:
        items.append(Div(Svg(Polygon(points=HEX_POINTS), viewBox="0 0 100 86.6", cls="cj-hex-shape"),
                         cls="cj-hex fog", style=box(*pos), aria_hidden="true"))
    for pos, key in MAP_LAYOUT.items():
        t = tiles.get(key)
        if not t:
            continue
        level = t.get("level")
        items.append(A(
            Svg(Polygon(points=HEX_POINTS), viewBox="0 0 100 86.6", cls="cj-hex-shape", aria_hidden="true"),
            Span(t["name"], cls="cj-hex-name"),
            stars(level, cls="cj-hex-stars") if level is not None else
            (Span(t["sub"], cls="cj-hex-sub") if t.get("sub") else ""),
            href=href(key), style=box(*pos),
            cls=" ".join(x for x in ("cj-hex", t.get("kind", ""), t.get("state", ""),
                                     "sel" if key == selected else "") if x),
            aria_current="true" if key == selected else None,
        ))
    return Div(*items, cls="cj-hexmap", role="navigation", aria_label=label,
               style=f"padding-top:{100 * map_h / 100:.3f}%")
