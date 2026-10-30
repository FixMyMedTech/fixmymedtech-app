# ui.py — shared pieces of the community journey pages.
#
# Every style comes from the FixMyMedTech design system tokens (the .cj-*
# classes in components.py). Role names come from the catalogue (the
# community team edits them); every other string is in i18n.py.

import json
import re

from fasthtml.common import *

import features.auth.helper as auth_helper
import features.profile.api as profile_api
from components import lucide, DASHBOARD_PERMISSIONS
from countries import COUNTRIES


def role_name(role: dict | None, lang: str) -> str:
    names = (role or {}).get("names") or {}
    return names.get(lang) or names.get("en") or (role or {}).get("key", "")


def role_text(role: dict | None, field: str, lang: str) -> str:
    value = (role or {}).get(field) or {}
    return value.get(lang) or value.get("en") or ""


def place(holding: dict, _) -> str:
    if holding.get("team"):
        return _(f"cj.team.{holding['team']}")
    return holding.get("country") or ""


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


def requirement_label(req: dict, roles_by_key: dict, _, lang: str) -> str:
    kind, ref = req.get("kind"), req.get("ref")
    if kind == "role":
        return _("cj.req.role").format(role=role_name(roles_by_key.get(ref), lang))
    if kind == "metric":
        return _(f"cj.metric.{ref}").format(n=req.get("threshold") or 1)
    if kind == "quest":
        n = req.get("threshold") or 1
        label = _(f"cj.quest.{ref}")
        return f"{label} ({n})" if n > 1 else label
    if kind == "confirmation":
        return _("cj.req.confirmed_by").format(role=role_name(roles_by_key.get(ref), lang))
    return ref or ""


def requirement_list(reqs: list, roles_by_key: dict, _, lang: str, show_progress: bool = True):
    rows = []
    for r in reqs:
        met = bool(r.get("met"))
        detail = ""
        if show_progress and r.get("kind") in ("metric", "quest") and (r.get("needed") or 1) > 1:
            detail = Span(f"{r.get('done', 0)} / {r.get('needed')}", cls="cj-small")
        rows.append(Div(
            check_mark(met) if show_progress else Span(cls="cj-check", aria_hidden="true"),
            Div(Span(requirement_label(r, roles_by_key, _, lang), cls="cj-quest-title"), detail,
                cls="cj-quest-body"),
            cls="cj-quest" + (" done" if met and show_progress else ""),
        ))
    return Div(*rows) if rows else P(_("cj.role.no_requirements"))


def country_select(name: str, value: str, _, required: bool = False, id: str = None):
    return Select(
        Option(_("cj.form.choose_country"), value=""),
        *[Option(c, value=c, selected=(c == value)) for c in COUNTRIES],
        name=name, id=id or name, cls="input", required=required,
    )


def has_dashboard(req) -> bool:
    return bool(set(req.session.get("community_permissions") or []) & set(DASHBOARD_PERMISSIONS))


def perms(req) -> set:
    return set(req.session.get("community_permissions") or [])


async def refresh_session(req, token: str) -> None:
    """Re-read /api/auth/me after a community change (status, roles)."""
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
    ("roles",      "/community/admin/roles",      None),
    ("history",    "/community/admin/history",    "view_role_history"),
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
