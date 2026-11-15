# components.py — reusable FastHTML UI components

import json
from contextvars import ContextVar

from fasthtml.common import *
from i18n import LANGUAGES, t as make_t

_user_ctx: ContextVar[dict] = ContextVar("current_user_ctx", default={})


def set_current_user(data: dict) -> None:
    """Store the current request's user display info (set per request)."""
    _user_ctx.set(data)


def current_user_ctx() -> dict:
    """Return the current user display info: name, username, email, avatar."""
    return _user_ctx.get()


# ── Avatar rendering, shared by pages/profile/my_profile and profile_detail ──
AVATAR_IMG_STYLE = (
    "width:110px;height:110px;border-radius:50%;object-fit:cover;"
    "background:var(--c-bg-2);border:2px solid var(--c-border);"
)
TRANSPARENT_GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="


# ── Favicons and app icons, shared by every page <head> ──────
def brand_head():
    """Favicon, touch icon and web manifest links (files in static/)."""
    return (
        Link(rel="icon", href="/favicon.ico", sizes="48x48"),
        Link(rel="icon", type="image/png", sizes="32x32", href="/static/favicon-32.png"),
        Link(rel="apple-touch-icon", href="/static/apple-touch-icon.png"),
        Link(rel="manifest", href="/static/site.webmanifest"),
        Meta(name="theme-color", content="#01437a"),
    )


# ── PostHog browser analytics (pageviews, autocapture, replay) ──
_POSTHOG_SNIPPET = """!function(t,e){var o,n,p,r;e.__SV||(window.posthog&&window.posthog.__loaded)||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey canRenderSurveyAsync identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing get_explicit_consent_status is_capturing clear_opt_in_out_capturing debug getPageViewId captureTraceFeedback captureTraceMetric".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);"""


def posthog_head():
    """posthog-js loader + identify, when POSTHOG_PROJECT_TOKEN/HOST are set.

    The browser is identified with the same profile id the server-side
    posthog-python events use, so both land on one person.
    """
    import os
    token = os.getenv("POSTHOG_PROJECT_TOKEN", "")
    host = os.getenv("POSTHOG_HOST", "")
    if not token or not host:
        return ()
    config = {
        "api_host": host.rstrip("/"),
        "defaults": "2025-05-24",
        "person_profiles": "identified_only",
        # Error tracking: uncaught errors and unhandled promise rejections.
        "capture_exceptions": True,
    }
    user = current_user_ctx()
    user_id = user.get("id") or ""
    props = {k: user[k] for k in ("email", "name") if user.get(k)}
    if user_id:
        after = f"posthog.identify({_js_json(user_id)}, {_js_json(props)});"
    else:
        # Signed out (or session expired): drop the previous user's identity.
        after = "if (posthog.get_property('$user_state') === 'identified') posthog.reset();"
    return (Script(
        _POSTHOG_SNIPPET
        + f"posthog.init({_js_json(token)}, {_js_json(config)});"
        + after
    ),)


def _js_json(value) -> str:
    """JSON safe to embed inside a <script> block."""
    return (json.dumps(value)
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


# ── Design tokens ────────────────────────────────────────────
CSS = """
:root {
  /* Type: the design system's system sans (fast on slow connections). */
  --font-body: var(--font-sans);
  --font-display: var(--font-sans);
  --font-mono: ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace;

  /* Old --c-* names, kept for one release as aliases of the design-system
     tokens below (docs/design-system/README.md, "Moving the app onto this
     system"). New code uses the token names directly. Because they point at
     the tokens, the dark theme needs no copy of them. */
  --c-bg:          var(--bg);
  --c-bg-2:        var(--sunken);
  --c-surface:     var(--surface);
  --c-border:      var(--border);
  --c-primary:     var(--primary);
  --c-primary-lt:  var(--primary-tint);
  --c-primary-mid: var(--primary-hover);
  --c-text:        var(--text);
  --c-text-2:      var(--text-muted);
  --c-text-3:      var(--text-muted);
  --c-green:       var(--ok);
  --c-green-lt:    var(--ok-tint);
  --c-amber:       var(--warn);
  --c-amber-lt:    var(--warn-tint);
  --c-red:         var(--danger);
  --c-red-lt:      var(--danger-tint);
  --c-blue:        var(--primary);
  --c-blue-lt:     var(--primary-tint);

  /* legacy aliases used by inline styles */
  --color-text:  var(--text);
  --color-bg-0:  var(--bg);
  --color-bg-1:  var(--bg);
  --color-bg-2:  var(--sunken);
  --color-theme-1: var(--primary);
  --color-theme-2: var(--primary-hover);


  /* FixMyMedTech design system tokens (docs/design-system/tokens.json). */
  --brand-teal: #1fb0a9;
  --brand-deep: #01437a;
  --brand-navy: #132b45;
  --on-brand: #ffffff;
  --bg: #f4f8fb;
  --surface: #ffffff;
  --sunken: #e9f0f5;
  --border: #d5e0e9;
  --border-strong: #728599;
  --text: #132b45;
  --text-muted: #4f6276;
  --primary: #026fa8;
  --primary-hover: #01437a;
  --primary-tint: #e0f0f8;
  --on-primary: #ffffff;
  --accent: #007c88;
  --accent-tint: #dff4f3;
  --lead: #5b3fa8;
  --lead-tint: #ece6fa;
  --frame: #132b45;
  --ok: #15803d;
  --ok-tint: #dcfce7;
  --warn: #b45309;
  --warn-tint: #fef3c7;
  --danger: #b91c1c;
  --danger-tint: #fee2e2;
  --shadow-card: 0 1px 2px rgba(19,43,69,0.05);
  --shadow-float: 0 12px 32px rgba(19,43,69,0.14);
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --radius-control: 8px;
  --radius-card: 14px;
  --radius-panel: 18px;
  --radius-tile: 10px;
  --radius-pill: 9999px;
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", Ubuntu, Cantarell, "Adwaita Sans", sans-serif;
  --font-mono-ds: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", "Noto Sans Mono", monospace;
  --gradient-brand: linear-gradient(135deg, var(--brand-teal) 0%, var(--brand-deep) 100%);

  --sidebar-w: 248px;
  --topbar-h: 56px;
  --r-sm: 6px; --r-md: 8px; --r-lg: 14px;
}

:root[data-theme="dark"] {
  --bg: #0b1a2c;
  --surface: #13283f;
  --sunken: #112538;
  --border: #26405a;
  --border-strong: #6a85a0;
  --text: #e6eef5;
  --text-muted: #a9bccd;
  --primary: #4fb6e8;
  --primary-hover: #8acff0;
  --primary-tint: #0e3550;
  --on-primary: #0b1a2c;
  --accent: #3cc3cf;
  --accent-tint: #0f3a3d;
  --lead: #b9a4f5;
  --lead-tint: #2c2350;
  --frame: #33506e;
  --ok: #4ade80;
  --ok-tint: #12391f;
  --warn: #fbbf24;
  --warn-tint: #3d2a0a;
  --danger: #f87171;
  --danger-tint: #44161a;
  --shadow-card: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-float: 0 12px 32px rgba(0,0,0,0.55);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font-body); font-size: 14px; background: var(--c-bg); color: var(--c-text); -webkit-font-smoothing: antialiased; }
::selection { background: var(--c-primary-lt); }
h1,h2,h3 { font-family: var(--font-display); line-height: 1.25; font-weight: 700; letter-spacing: -.01em; text-wrap: balance; }
h1 { font-size: clamp(1.5rem, 2.6vw, 1.875rem); letter-spacing: -.02em; line-height: 1.15; } h2 { font-size: 1.125rem; } h3 { font-size: 1rem; }
p { color: var(--c-text-2); font-size: 0.875rem; line-height: 1.65; }
a { color: var(--c-primary); text-decoration: none; }

/* ── Top navigation bar ───────────────────────────────────── */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; height: var(--topbar-h);
  display: flex; align-items: center; gap: 10px; padding: 0 14px;
  /* Brand bar (platform brief): solid brand-deep with the 4px gradient rule. */
  background: var(--brand-deep); color: var(--on-brand);
  border-bottom: 4px solid transparent; border-image: var(--gradient-brand) 1;
  z-index: 400;
}
.togg-btn {
  width: 36px; height: 36px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--r-md);
  background: transparent; color: var(--c-text-2); font-size: 1.05rem;
  cursor: pointer; transition: background .15s, color .15s;
}
.togg-btn:hover { background: var(--c-bg-2); color: var(--c-primary); }
.topbar .togg-btn { color: var(--on-brand); }
.topbar .togg-btn:hover { background: rgba(255,255,255,.14); color: var(--on-brand); }
.brand {
  display: flex; align-items: center; gap: 9px;
  font-family: var(--font-display); font-weight: 700; font-size: 1rem;
  letter-spacing: -.01em; color: var(--c-text);
}
.brand:hover { color: var(--c-text); }
.brand-mark {
  width: 28px; height: 28px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm); background: var(--c-primary); color: #fff;
  font-size: .95rem; font-weight: 600;
}
.brand-logo { height: 30px; width: auto; flex-shrink: 0; display: block; }
.topbar .brand, .topbar .brand:hover { color: var(--on-brand); }
.topbar .brand-logo { height: 26px; }
.brand-sub { color: var(--c-text-3); font-weight: 500; font-size: .82rem; }
.topbar .avatar-btn { border: 2px solid rgba(255,255,255,.55); background: rgba(255,255,255,.14); color: var(--on-brand); }
.topbar .avatar-btn:hover { border-color: var(--on-brand); }
.topbar .btn-secondary { background: rgba(255,255,255,.12); color: var(--on-brand); border-color: rgba(255,255,255,.45); }
.topbar .btn-secondary:hover { background: rgba(255,255,255,.22); color: var(--on-brand); border-color: var(--on-brand); }
.topbar .input-lang { background: rgba(255,255,255,.12); color: var(--on-brand); border-color: rgba(255,255,255,.45); }
.topbar .input-lang option { color: var(--text); background: var(--surface); }
.top-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }

/* ── App shell ────────────────────────────────────────────── */
.shell { display: flex; min-height: 100vh; }
.sidebar {
  position: fixed; top: var(--topbar-h); left: 0; bottom: 0;
  width: var(--sidebar-w);
  display: flex; flex-direction: column;
  background: var(--c-surface); border-right: 1px solid var(--c-border);
  z-index: 300; transition: width .2s ease, transform .2s ease;
}
.sb-head { display: none; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--c-border); }
.sb-nav { flex: 1; padding: 12px 10px; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; overflow-x: hidden; }
/* Sidebar sections (platform brief): each group has its audience colour —
   equipment work in primary blue, growing the network in teal, community in
   lead purple. The icon sits in a small rounded tile of that colour. */
.nav-sec { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--text-muted); padding: 14px 10px 6px; white-space: nowrap; }
.nav-link {
  --tone: var(--primary); --tone-tint: var(--primary-tint);
  display: flex; align-items: center; gap: 10px;
  padding: 6px 8px; border-radius: 10px;
  font-size: .875rem; font-weight: 500;
  color: var(--c-text-2); text-decoration: none; white-space: nowrap;
  transition: background .15s, color .15s;
}
.nav-link.t-eng { --tone: var(--accent); --tone-tint: var(--accent-tint); }
.nav-link.t-lead { --tone: var(--lead); --tone-tint: var(--lead-tint); }
.nav-link:hover { background: var(--c-bg-2); color: var(--c-text); }
.nav-link.active { background: var(--tone-tint); color: var(--text); font-weight: 700; }
.nav-ico { width: 30px; height: 30px; flex-shrink: 0; display: grid; place-items: center; border-radius: 9px; background: var(--tone-tint); color: var(--tone); transition: background .15s, color .15s, transform .15s; }
.nav-ico svg { width: 17px; height: 17px; display: block; }
.nav-link:hover .nav-ico { transform: scale(1.06); }
.nav-link.active .nav-ico { background: var(--tone); color: var(--surface); }
body.sidebar-collapsed .nav-sec { display: none; }
.nav-menu-ico svg { width: 16px; height: 16px; display: inline-block; vertical-align: -3px; margin-right: 6px; }
.sb-foot {
  padding: 12px 14px; border-top: 1px solid var(--c-border);
  display: flex; flex-direction: column; gap: 8px;
}
.sb-foot .input-lang { width: 100%; }
.sb-foot .theme-btn { width: 100%; height: 34px; }
.main {
  margin-left: var(--sidebar-w); flex: 1;
  min-width: 0; /* a flex item defaults to min-width:auto, so a wide table or long URL would stretch the page past the phone screen */
  padding: calc(var(--topbar-h) + 22px) 28px 32px;
  transition: margin-left .2s ease;
}

/* Collapsed sidebar (desktop fold) */
body.sidebar-collapsed .sidebar { width: 64px; }
body.sidebar-collapsed .main { margin-left: 64px; }
body.sidebar-collapsed .nav-link { justify-content: center; padding: 5px 0; }
body.sidebar-collapsed .nav-label { display: none; }
body.sidebar-collapsed .sb-foot { display: none; }

/* Buttons */
.btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; padding:8px 16px; border-radius:var(--r-md); font-family:var(--font-body); font-size:.875rem; font-weight:500; line-height:1.4; cursor:pointer; transition:all .15s; border:1px solid transparent; text-decoration:none; }
.btn-primary { background:var(--c-primary); color:#fff; }
.btn-primary:hover { background:var(--c-primary-mid); }
.btn-secondary { background:var(--surface); color:var(--text); border-color:var(--border-strong); }
.btn-secondary:hover { border-color:var(--c-primary); color:var(--c-primary); }
.btn-danger { background:var(--c-red-lt); color:var(--c-red); border:1px solid transparent; }
/* btn-warning and btn-outline are merged into btn-secondary (design system). */
.btn-warning { background:var(--surface); color:var(--text); border:1px solid var(--border-strong); }
.btn-warning:hover { border-color:var(--primary); color:var(--primary); }
.btn-sm { padding:4px 10px; font-size:.8rem; }
.btn svg { width:16px; height:16px; flex-shrink:0; }
.btn-primary { font-weight:600; }
.btn-light { background:var(--on-brand); color:var(--brand-deep); }
.btn-outline { background:var(--surface); color:var(--text); border:1px solid var(--border-strong); }
.btn-outline:hover { border-color:var(--primary); color:var(--primary); }
.oauth-divider { text-align:center; font-size:.78rem; color:var(--c-text-3); margin:6px 0 10px; position:relative; }
.oauth-divider::before, .oauth-divider::after { content:""; position:absolute; top:50%; width:34%; height:1px; background:var(--c-border); }
.oauth-divider::before { left:0; }
.oauth-divider::after { right:0; }
.oauth-buttons { display:flex; flex-direction:column; gap:8px; }

/* Cards */
.card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--radius-card); padding:20px 22px; box-shadow:var(--shadow-card); }
.card-title { font-size:1rem; font-weight:600; margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid var(--c-border); }
.profile-basic { display:flex; gap:24px; align-items:flex-start; }
.profile-photo-side { flex-shrink:0; display:flex; flex-direction:column; align-items:flex-start; }
.profile-photo-side input[type="file"] { max-width:170px; font-size:.78rem; }
.profile-fields { flex:1 1 auto; min-width:0; }

/* Badges */
.badge { display:inline-flex; align-items:center; gap:5px; padding:2px 10px; border-radius:9999px; font:700 11px/1.6 var(--font-sans); letter-spacing:.02em; white-space:nowrap; }
/* Status dot in the badge colour (platform brief chips): colour + word. */
.badge::before { content:""; width:6px; height:6px; border-radius:50%; background:currentColor; flex-shrink:0; }
/* Old badge names, aliases of badge-ok / -warn / -danger / -neutral. */
.badge-green { background:var(--ok-tint); color:var(--ok); }
.badge-amber { background:var(--warn-tint); color:var(--warn); }
.badge-red   { background:var(--danger-tint); color:var(--danger); }
.badge-blue  { background:var(--primary-tint); color:var(--primary); }
.badge-gray  { background:var(--sunken); color:var(--text-muted); }

/* Forms */
.input { width:100%; padding:9px 13px; border:1px solid var(--c-border); border-radius:var(--r-md); font-family:var(--font-body); font-size:.875rem; background:var(--c-surface); color:var(--c-text); transition:border-color .15s, box-shadow .15s; }
.input:focus { outline:none; border-color:var(--c-primary); box-shadow:0 0 0 3px var(--c-primary-lt); }
.label { display:block; font-size:.8rem; font-weight:500; color:var(--c-text-2); margin-bottom:5px; }
.form-group { margin-bottom:14px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }

/* Tables */
.table-wrap { overflow-x:auto; border:1px solid var(--c-border); border-radius:var(--radius-card); background:var(--surface); box-shadow:var(--shadow-card); }
table { width:100%; border-collapse:collapse; font-size:.875rem; }
th { text-align:left; padding:10px 14px; font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--c-text-3); background:var(--c-bg-2); border-bottom:1px solid var(--c-border); }
td { padding:11px 14px; border-bottom:1px solid var(--c-border); color:var(--c-text-2); }
tr:last-child td { border-bottom:none; }
tr:hover td { background:var(--c-bg-2); }

/* Row action buttons */
.actions { display:flex; gap:8px; justify-content:flex-end; flex-wrap:wrap; }

/* Device search: input with a suggestion dropdown */
.dev-search { position:relative; margin-bottom:14px; }
.dev-sugg {
  position:absolute; top:calc(100% + 4px); left:0; right:0; z-index:60;
  background:var(--c-surface); border:1px solid var(--c-border);
  border-radius:var(--r-md); box-shadow:0 8px 24px rgba(0,0,0,.16);
  max-height:320px; overflow:auto;
}
.sugg-item {
  display:flex; flex-direction:column; gap:2px;
  padding:9px 12px; text-decoration:none; color:inherit;
  border-bottom:1px solid var(--c-border);
}
.sugg-item:last-child { border-bottom:none; }
.sugg-item:hover, .sugg-item:focus { background:var(--c-bg-2); outline:none; }
.sugg-name { font-size:.875rem; font-weight:500; color:var(--c-text); }
.sugg-sub { font-size:.72rem; color:var(--c-text-3); }
.sugg-empty { padding:10px 12px; font-size:.8rem; color:var(--c-text-3); }

/* Devices page: below 768px the table becomes stacked cards.
   Only applies to tables flagged .has-cards, so other tables keep scrolling. */
@media (max-width: 768px) {
  .table-wrap.has-cards { border:none; background:none; border-radius:0; overflow:visible; }
  .table-wrap.has-cards table,
  .table-wrap.has-cards tbody,
  .table-wrap.has-cards tr,
  .table-wrap.has-cards td { display:block; width:100%; }
  .table-wrap.has-cards thead { display:none; }
  .table-wrap.has-cards tbody { display:grid; gap:12px; }
  .table-wrap.has-cards tbody tr {
    border:1px solid var(--c-border); border-radius:var(--r-lg);
    background:var(--c-surface); padding:14px 16px;
    box-shadow:0 1px 3px rgba(0,0,0,.05);
  }
  .table-wrap.has-cards tbody tr:hover td { background:transparent; }
  .table-wrap.has-cards td {
    display:flex; justify-content:space-between; align-items:flex-start;
    gap:12px; padding:8px 0; border-bottom:1px solid var(--c-border);
  }
  /* First cell is the card header: name + category + model, no label. */
  .table-wrap.has-cards td:first-child { display:block; padding-top:0; }
  .table-wrap.has-cards td:last-child { border-bottom:none; padding-bottom:0; }
  .table-wrap.has-cards td[data-label]::before {
    content:attr(data-label); flex:0 0 auto; padding-top:3px;
    font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
    color:var(--c-text-3);
  }
  .table-wrap.has-cards .actions { width:100%; justify-content:stretch; }
  .table-wrap.has-cards .actions .btn { flex:1; text-align:center; }
}

/* Alerts */
.alert { padding:11px 14px; border-radius:var(--r-md); font-size:.875rem; margin-bottom:14px; }
.alert-error   { background:var(--c-red-lt);   color:var(--c-red);   border:1px solid transparent; }
.alert-success { background:var(--c-green-lt); color:var(--c-green); border:1px solid transparent; }
.alert-warning { background:var(--c-amber-lt); color:var(--c-amber); border:1px solid transparent; }

/* Stats grid */
.stat-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:12px; margin-bottom:20px; }
.stat-card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--radius-card); padding:16px 18px; border-top:3px solid var(--border-strong); }
.stat-label { font-size:11px; font-weight:700; color:var(--c-text-3); text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }
.stat-num { font-family:var(--font-display); font-size:2rem; font-weight:800; color:var(--c-text); line-height:1; font-variant-numeric:tabular-nums; letter-spacing:-.02em; }
.stat-sub { font-size:.72rem; color:var(--c-text-3); margin-top:3px; }
.stat-card.g { border-top:3px solid var(--c-green); }
.stat-card.a { border-top:3px solid var(--c-amber); }
.stat-card.r { border-top:3px solid var(--c-red); }
.stat-card.p { border-top:3px solid var(--c-primary); }

/* Two col */
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:14px; }

/* Organization ownership: 3 labelled columns, stacked on mobile. */
.own-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px,1fr)); gap:12px; }
.own-col { display:flex; flex-direction:column; align-items:flex-start; gap:2px; min-width:0; padding:12px; border:1px solid var(--c-border); border-radius:var(--r-md); background:var(--c-bg-2); }
.own-label { font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--c-text-3); }
.own-name { font-size:.95rem; font-weight:600; color:var(--c-text); overflow-wrap:anywhere; }

/* Network directory: one card per member, the whole card a link. */
.net-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:12px; margin:18px auto 0;}
.net-card { display:flex; flex-direction:column; align-items:center; text-align:center; gap:2px; padding:18px 14px; border:1px solid var(--c-border); border-radius:var(--r-lg); background:var(--c-surface); text-decoration:none; color:var(--c-text); transition:border-color .15s, transform .15s, box-shadow .15s; }
.net-card:hover { border-color:var(--c-primary); transform:translateY(-2px); box-shadow:0 4px 14px rgba(0,0,0,.08); }
.net-avatar { width:64px; height:64px; border-radius:50%; object-fit:cover; flex-shrink:0; }
.net-initials { display:flex; align-items:center; justify-content:center; background:var(--c-primary-lt); color:var(--c-primary); font-weight:700; font-size:1.25rem; }
.net-name { font-weight:600; font-size:.95rem; margin-top:8px; overflow-wrap:anywhere; }
.net-username { font-size:.8rem; color:var(--c-text-3); }
.net-country { font-size:.8rem; color:var(--c-text-2); }
.net-role { font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--c-primary); margin-top:4px; }
.net-org { font-size:.8rem; color:var(--c-text-3); overflow-wrap:anywhere; }

/* Toolbar: search on the left, cards/list switch on the right. */
.net-toolbar { display:flex; gap:12px; align-items:center; justify-content:space-between; flex-wrap:wrap; margin-top:14px; }
.net-toolbar form { flex:1 1 auto; }
.net-view { display:inline-flex; border:1px solid var(--c-border); border-radius:var(--r-md); overflow:hidden; background:var(--c-surface); flex-shrink:0; }
.net-view-btn { padding:7px 14px; font-size:.875rem; font-weight:500; color:var(--c-text-2); text-decoration:none; transition:background .15s, color .15s; }
.net-view-btn:hover { background:var(--c-bg); color:var(--c-text); }
.net-view-btn.is-active { background:var(--c-primary); color:#fff; }

/* List view: the same members, sortable by column. */
.net-table-wrap { overflow-x:auto; margin-top:18px; border:1px solid var(--c-border); border-radius:var(--r-lg); background:var(--c-surface); }
.net-table { width:100%; border-collapse:collapse; font-size:.9rem; }
.net-table th { text-align:left; padding:11px 14px; border-bottom:1px solid var(--c-border); font-weight:600; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; color:var(--c-text-2); white-space:nowrap; }
.net-table td { padding:10px 14px; border-bottom:1px solid var(--c-border); }
.net-table tbody tr:last-child td { border-bottom:none; }
.net-table tbody tr:hover { background:var(--c-bg); }
.net-th-name { min-width:220px; }
.net-num { text-align:right; font-variant-numeric:tabular-nums; color:var(--c-text-2); }
.net-sort { display:inline-flex; align-items:center; gap:4px; color:inherit; text-decoration:none; }
.net-sort:hover { color:var(--c-primary); }
.net-sort.is-active { color:var(--c-primary); }
.net-sort-ico { font-size:.8em; line-height:1; }
.net-td-name { padding-top:6px; padding-bottom:6px; }
.net-row-link { display:flex; align-items:center; gap:10px; color:var(--c-text); text-decoration:none; }
.net-row-link:hover .net-name { color:var(--c-primary); }
.net-row-text { min-width:0; }
.net-row-text .net-name { margin-top:0; }
.net-avatar-sm { width:34px; height:34px; font-size:.85rem; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:22px; }

/* Toolbar */
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
.pill { padding:5px 14px; border-radius:9999px; font-size:.8rem; font-weight:600; background:var(--c-surface); border:1px solid var(--border-strong); color:var(--c-text-2); cursor:pointer; text-decoration:none; transition:border-color .15s, color .15s; }
.pill:hover { border-color:var(--primary); color:var(--primary); }
.pill.active { background:var(--c-primary); color:#fff; border-color:var(--c-primary); }

/* Public QR page */
.pub-page { max-width:520px; margin:0 auto; min-height:100vh; display:flex; flex-direction:column; background:var(--c-surface); border-left:1px solid var(--c-border); border-right:1px solid var(--c-border); }
.pub-header {
  background: var(--brand-deep);
  border-bottom: 3px solid transparent; border-image: var(--gradient-brand) 1;
  padding:12px 16px; display:flex; align-items:center; justify-content:space-between;
}
.pub-logo { display:flex; align-items:center; gap:7px; color:#fff; font-family:var(--font-display); font-weight:700; font-size:1rem; }
.pub-cross { color:#5eead4; }
.device-identity { display:flex; align-items:flex-start; gap:12px; padding:16px; background:var(--c-surface); border-bottom:1px solid var(--c-border); }
.dev-icon { font-size:2rem; flex-shrink:0; }
.dev-cat { font-size:11px; font-weight:700; color:var(--c-text-3); text-transform:uppercase; letter-spacing:.08em; }
.dev-name { font-size:1.2rem; font-family:var(--font-display); font-weight:700; margin:2px 0; }
.dev-meta { font-size:.78rem; color:var(--c-text-3); }
.dev-status { flex-shrink:0; text-align:right; }
.dev-loc { font-size:.72rem; color:var(--c-text-3); margin-top:4px; }
.warn-bar { display:flex; gap:8px; align-items:flex-start; background:var(--c-amber-lt); border-left:4px solid var(--c-amber); padding:11px 14px; font-size:.85rem; color:var(--c-amber); }
.warn-bar p { color:var(--c-amber); font-size:.78rem; margin:2px 0 0; }
.report-cta { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:var(--c-surface); border-bottom:1px solid var(--c-border); }
.pub-tabs { display:flex; background:var(--c-surface); border-bottom:1px solid var(--c-border); margin-top:6px; }
.pub-tab { flex:1; padding:10px 6px; font-size:.85rem; font-weight:500; color:var(--c-text-3); background:none; border:none; cursor:pointer; border-bottom:2px solid transparent; text-align:center; text-decoration:none; }
.pub-tab.active { color:var(--c-primary); border-bottom-color:var(--c-primary); }
.info-list { display:flex; flex-direction:column; padding:8px 16px; }
.info-row { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--c-border); font-size:.875rem; }
.info-row:last-child { border-bottom:none; }
.info-row dt { color:var(--c-text-3); font-weight:500; }
.info-row dd { color:var(--c-text); font-weight:500; }
.pub-section { padding:14px 16px; }
.pub-footer { margin-top:auto; padding:16px; text-align:center; border-top:1px solid var(--c-border); font-size:.75rem; color:var(--c-text-3); }

/* Login / Signup */
.auth-wrap { min-height:100vh; display:grid; grid-template-columns:440px 1fr; }
.auth-card { padding:48px 40px; display:flex; flex-direction:column; justify-content:center; background:var(--c-surface); border-right:1px solid var(--c-border); }
.auth-brand { margin-bottom:28px; }
.brand-icon { font-size:1.8rem; color:var(--c-primary); display:block; margin-bottom:8px; }
.auth-bg {
  background: var(--gradient-brand);
  display:flex; align-items:flex-end; padding:48px; position:relative; overflow:hidden;
}
/* The white Africa logo, large and calm, as the panel's picture. */
.auth-bg::before { content:''; position:absolute; top:8%; right:8%; width:min(46%, 420px); aspect-ratio:1; background:url(/static/brand/fixmymedtech-africa-white.png) center/contain no-repeat; opacity:.9; }
.step-num { flex:0 0 32px; width:32px; height:32px; border-radius:50%; background:var(--on-brand); color:var(--brand-deep); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:.9rem; }
.auth-steps { position:relative; width:100%; }
.auth-quote { position:relative; font-family:var(--font-display); font-size:clamp(1.4rem, 2.4vw, 2rem); color:var(--on-brand); line-height:1.25; letter-spacing:-.015em; border-left:4px solid var(--on-brand); padding-left:20px; font-weight:700; max-width:22ch; }
.auth-quote em { color:var(--on-brand); font-style:normal; opacity:.8; }
.auth-link { margin-top:14px; font-size:.82rem; color:var(--c-text-3); text-align:center; }
.auth-link a { color:var(--c-primary); font-weight:500; }

/* Overdue */
.overdue { color:var(--c-red); font-weight:500; }
.overdue-tag { display:inline-block; margin-left:3px; background:var(--c-red-lt); color:var(--c-red); font-size:.7rem; padding:1px 5px; border-radius:10px; }

/* Theme toggle + avatar (top-right) */
.theme-btn {
  width:36px; height:36px; display:flex; align-items:center; justify-content:center;
  border:1px solid var(--c-border); background:var(--c-surface);
  color:var(--c-text-2); border-radius:var(--r-md); cursor:pointer; font-size:1rem;
  transition: border-color .15s, color .15s;
}
.theme-btn:hover { border-color:var(--c-primary); color:var(--c-primary); }
.pub-theme { position:fixed; top:16px; right:16px; z-index:600; }
.lang-fab { position:fixed; bottom:16px; left:16px; z-index:600; }
.avatar-wrap { position:relative; }
.avatar-btn {
  width:38px; height:38px; border-radius:50%;
  background:var(--c-bg-2); color:var(--c-text); border:1px solid var(--c-border);
  cursor:pointer; font-size:1.05rem; display:flex; align-items:center; justify-content:center;
  overflow:hidden; padding:0; transition: border-color .15s;
}
.avatar-btn:hover { border-color:var(--c-primary); }
.avatar-menu {
  position:absolute; top:calc(100% + 10px); right:0; min-width:200px;
  background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--r-lg);
  box-shadow:0 12px 32px rgba(15,23,42,.12); display:none; flex-direction:column; padding:6px;
}
.avatar-menu.open { display:flex; }
.avatar-menu-user { padding:10px 12px 9px; border-bottom:1px solid var(--c-border); margin-bottom:6px; display:flex; flex-direction:column; gap:2px; }
.avatar-menu-name { font-size:.875rem; font-weight:600; color:var(--c-text); overflow-wrap:anywhere; }
.avatar-menu-email { font-size:.75rem; color:var(--c-text-3); overflow-wrap:anywhere; }
.avatar-menu a { display:flex; align-items:center; gap:8px; padding:9px 12px; border-radius:var(--r-md); font-size:.875rem; font-weight:500; color:var(--c-text-2); text-decoration:none; }
.avatar-menu a:hover { background:var(--c-bg-2); color:var(--c-primary); }
.avatar-menu form { padding: 0 8px 4px; }
.avatar-menu .input-lang { width: 100%; }

/* Language select */
.input-lang {
  padding:5px 9px; border:1px solid var(--c-border);
  border-radius:var(--r-md); font-size:.75rem; font-family:var(--font-mono);
  background:var(--c-surface); color:var(--c-text);
  cursor:pointer; outline:none;
}
.input-lang:focus { border-color:var(--c-primary); }

/* Organization healthsites manager */
.hs-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:8px; }
.hs-grid > div { min-width:0; }

/* Public pages (no sidebar): content starts below the fixed top bar */
.public-shell .pub-page { padding-top: var(--topbar-h); }

/* ── World switcher (three worlds) ────────────────────────────
   Tabs in the brand bar on wide screens, a bottom tab bar on phones. */
.worlds { display:flex; gap:4px; }
.wt { --tone: var(--primary); display:flex; align-items:center; gap:7px; text-decoration:none; font-weight:600; white-space:nowrap; }
.wt.w-work { --tone: var(--accent); } .wt.w-community { --tone: var(--lead); }
.wt-ico { display:grid; place-items:center; }
.wt-ico svg { width:17px; height:17px; display:block; }
.worlds-top { margin:0 auto; padding:4px; border-radius:12px; background:rgba(255,255,255,.12); }
.worlds-top .wt { padding:5px 14px; border-radius:9px; font-size:.84rem; color:var(--on-brand); opacity:.85; transition:background .15s, opacity .15s; }
.worlds-top .wt:hover { background:rgba(255,255,255,.14); opacity:1; }
.worlds-top .wt.on { background:var(--surface); color:var(--tone); opacity:1; font-weight:700; }
.worlds-bottom { display:none; }
@media (max-width: 768px) {
  .worlds-top { display:none; }
  .worlds-bottom {
    display:grid; grid-auto-flow:column; grid-auto-columns:1fr; gap:0;
    position:fixed; left:0; right:0; bottom:0; z-index:280;
    background:var(--surface); border-top:1px solid var(--border);
    padding:4px 8px calc(4px + env(safe-area-inset-bottom, 0px));
  }
  .worlds-bottom .wt { flex-direction:column; gap:2px; padding:4px 0; font-size:.7rem; color:var(--text-muted); }
  .worlds-bottom .wt-ico { width:44px; height:26px; border-radius:13px; transition:background .15s, color .15s; }
  .worlds-bottom .wt.on { color:var(--tone); font-weight:700; }
  .worlds-bottom .wt.on .wt-ico { background:var(--tone); color:var(--surface); }
  /* Room for the tab bar: lift the "?" button and the page end above it. */
  body:has(.worlds-bottom) { --worlds-h: 58px; }
  body:has(.worlds-bottom) .fb-widget { bottom:calc(16px + var(--worlds-h) + env(safe-area-inset-bottom, 0px)); }
  body:has(.worlds-bottom) .main { padding-bottom:calc(var(--fb-clearance) + var(--worlds-h)); }
}
@media print { .worlds { display:none; } }
/* World doors on /home: one big door per unlocked world. */
.doors { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; margin-top:18px; }
.door { --tone: var(--primary); --tone-tint: var(--primary-tint); display:flex; flex-direction:column; gap:10px; padding:20px; border-radius:var(--radius-panel, 18px); background:var(--surface); border:1px solid var(--border); border-top:5px solid var(--tone); text-decoration:none; color:var(--text); transition:transform .15s, box-shadow .15s, border-color .15s; }
.door.w-work { --tone: var(--accent); --tone-tint: var(--accent-tint); } .door.w-community { --tone: var(--lead); --tone-tint: var(--lead-tint); }
.door:hover { transform:translateY(-2px); box-shadow:0 14px 30px -20px var(--tone); }
.door-ico { width:52px; height:52px; border-radius:14px; display:grid; place-items:center; background:var(--tone); color:var(--surface); }
.door-ico svg { width:26px; height:26px; }
.door b { font-size:1.1rem; }
.door p { font-size:.85rem; }
.door-links { display:flex; flex-wrap:wrap; gap:6px; margin-top:auto; }
.door-links span { display:inline-flex; align-items:center; gap:5px; font-size:.75rem; font-weight:600; padding:3px 9px; border-radius:99px; background:var(--tone-tint); color:var(--tone); }
.door-links svg { width:13px; height:13px; }
@media (prefers-reduced-motion: reduce) { .door { transition:none; } .door:hover { transform:none; } }

/* Mobile: drawer sidebar */
.sb-toggle, .sb-close, .sb-backdrop { display:none; }

@media (max-width: 768px) {
  .sidebar {
    top:0; width:260px; height:100vh;
    transform:translateX(-100%);
    box-shadow:2px 0 24px rgba(0,0,0,.2);
  }
  .sidebar.open { transform:translateX(0); }
  .sb-head { display:flex; }
  .main { margin-left:0; padding:calc(var(--topbar-h) + 16px) 16px 24px; }
  body.sidebar-collapsed .main { margin-left:0; }
  .sb-backdrop {
    display:block; position:fixed; inset:0; z-index:290;
    background:rgba(0,0,0,.5); opacity:0; pointer-events:none;
    transition:opacity .2s ease;
  }
  .sb-backdrop.show { opacity:1; pointer-events:auto; }
  .sb-close {
    display:flex; align-items:center; justify-content:center;
    margin-left:auto; width:34px; height:34px; flex-shrink:0;
    border:none; border-radius:var(--r-md);
    background:var(--c-bg-2); color:var(--c-text-2); font-size:1rem; cursor:pointer;
  }
  .brand-sub { display:none; }
  .stat-grid { grid-template-columns:1fr 1fr; }
  .two-col { grid-template-columns:1fr; }
  .own-grid { grid-template-columns:1fr; }
  .auth-wrap { grid-template-columns:1fr; }
  .auth-bg { display:none; }
  .auth-card { padding:32px 20px; border-right:none; }
  .form-row { grid-template-columns:1fr; }
  .profile-basic { flex-direction:column; gap:8px; }
}

/* Feedback button (bottom-right, every page). z-index sits 10 above the
   highest fixed layer (.pub-theme / .lang-fab at 600). */
.fb-widget {
  position:fixed; z-index:610;
  right:calc(16px + env(safe-area-inset-right, 0px));
  bottom:calc(16px + env(safe-area-inset-bottom, 0px));
  display:flex; flex-direction:column; align-items:flex-end; gap:8px;
}
.fb-btn {
  width:44px; height:44px; border-radius:50%; border:none; cursor:pointer;
  background:var(--c-primary); color:#fff; font-size:1.15rem; font-weight:700;
  box-shadow:0 6px 18px rgba(15,23,42,.22); transition:background .15s, transform .15s;
}
.fb-btn:hover { background:var(--c-primary-mid); transform:translateY(-1px); }
.fb-btn:focus-visible { outline:3px solid var(--c-primary-lt); outline-offset:2px; }
.fb-menu {
  display:none; flex-direction:column; min-width:200px; padding:6px;
  background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--r-lg);
  box-shadow:0 12px 32px rgba(15,23,42,.16);
}
.fb-menu.open { display:flex; }
.fb-menu a { display:flex; align-items:center; gap:8px; padding:9px 12px; border-radius:var(--r-md); font-size:.875rem; font-weight:500; color:var(--c-text-2); }
.fb-menu a:hover, .fb-menu a:focus-visible { background:var(--c-bg-2); color:var(--c-primary); outline:none; }
@media print { .fb-widget { display:none; } }
/* Room at the end of every page so its last controls (e.g. the registration
   wizard's Next button) can scroll clear of the fixed "?" button:
   16px gap + 44px button + 24px breathing space, above the phone's home bar.
   Inside the full-height containers (box-sizing: border-box), so a short
   page doesn't become scrollable. */
:root { --fb-clearance: calc(84px + env(safe-area-inset-bottom, 0px)); }
.main, .public-shell, .pub-page { padding-bottom: var(--fb-clearance); }
@media (max-width: 768px) { .auth-wrap { padding-bottom: var(--fb-clearance); } }
@media print { .main, .public-shell, .pub-page, .auth-wrap { padding-bottom:0; } }

/* Feedback form page */
.fb-page { max-width:560px; margin:24px auto 80px; padding:0 16px; }
.public-shell .fb-page { padding-top:calc(var(--topbar-h) + 8px); }
.fb-types { display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap; }
.fb-type {
  flex:1 1 140px; display:flex; align-items:center; gap:8px; cursor:pointer;
  padding:10px 12px; border:1px solid var(--c-border); border-radius:var(--r-md); font-size:.875rem;
}
.fb-type:has(input:checked) { border-color:var(--c-primary); background:var(--c-primary-lt); }

/* Modal dialogs: center on screen with a dimmed backdrop */
dialog {
  margin:auto;
  position:fixed;
  inset:0;
  width:fit-content;
  height:fit-content;
  max-width:calc(100vw - 32px);
  max-height:calc(100vh - 32px);
  overflow:auto;
}
dialog::backdrop {
  background:rgba(15,23,42,.45);
}

/* Loading spinner (used by healthsites search, etc.) */
.spinner {
  width:16px; height:16px; flex-shrink:0;
  border:2px solid rgba(37,99,235,.25);
  border-top-color:var(--c-primary);
  border-radius:50%;
  animation:spin .6s linear infinite;
}
@keyframes spin { to { transform:rotate(360deg); } }

/* ── Community journey (design system tokens only) ───────────── */
.cj { display:flex; flex-direction:column; gap:var(--space-4); max-width:1032px; width:100%; }
.cj-narrow { max-width:640px; }
.cj h1 { font-size:24px; line-height:1.25; font-weight:700; color:var(--text); }
.cj h2 { font-size:20px; line-height:1.3; font-weight:700; color:var(--text); }
.cj h3 { font-size:16px; line-height:1.35; font-weight:600; color:var(--text); }
.cj p { color:var(--text-muted); font-size:14px; line-height:1.6; }
.cj-small { font-size:12px; line-height:1.4; font-weight:500; color:var(--text-muted); }
.cj-eyebrow { font-size:12px; line-height:1.4; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); }
.cj-hero { background:var(--gradient-brand); color:var(--on-brand); border-radius:var(--radius-panel); padding:var(--space-8) var(--space-6); display:flex; flex-direction:column; gap:var(--space-2); position:relative; overflow:hidden; }
.cj-hero > * { position:relative; max-width:calc(100% - 150px); }
.cj-hero::after { content:""; position:absolute; right:24px; top:50%; transform:translateY(-50%); width:130px; height:130px; background:url(/static/brand/fixmymedtech-africa-white.png) center/contain no-repeat; opacity:.9; pointer-events:none; }
@media (max-width:640px){ .cj-hero > * { max-width:none; } .cj-hero::after { width:84px; height:84px; top:16px; right:12px; transform:none; opacity:.35; } }
.cj-hero h1, .cj-hero h2, .cj-hero p, .cj-hero .cj-eyebrow { color:var(--on-brand); }
.cj-hero p { opacity:.92; }
.cj-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-card); box-shadow:var(--shadow-card); padding:var(--space-4) var(--space-6); display:flex; flex-direction:column; gap:var(--space-3); min-width:0; }
.cj-card.is-focus { border:2px solid var(--primary); }
.cj-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:var(--space-4); }
.cj-row { display:flex; flex-wrap:wrap; gap:var(--space-2); align-items:center; }
.cj-between { display:flex; justify-content:space-between; align-items:center; gap:var(--space-3); flex-wrap:wrap; }
.cj-quest { display:flex; gap:var(--space-3); align-items:flex-start; padding:var(--space-3) 0; border-top:1px solid var(--border); }
.cj-quest:first-child { border-top:0; }
.cj-check { width:24px; height:24px; flex-shrink:0; border-radius:9999px; border:2px solid var(--border-strong); display:flex; align-items:center; justify-content:center; color:var(--on-primary); }
.cj-check svg { width:14px; height:14px; }
.cj-quest.done .cj-check { background:var(--ok); border-color:var(--ok); }
.cj-quest-body { flex:1; display:flex; flex-direction:column; gap:var(--space-2); min-width:0; }
.cj-quest-title { font-size:14px; font-weight:600; color:var(--text); }
.cj-bar { height:6px; border-radius:9999px; background:var(--border); overflow:hidden; }
.cj-bar > span { display:block; height:6px; background:var(--primary); border-radius:9999px; }
.cj-hero .cj-bar { background:rgba(255,255,255,.3); }
.cj-hero .cj-bar > span { background:var(--on-brand); }
.badge-ok { background:var(--ok-tint); color:var(--ok); }
.badge-warn { background:var(--warn-tint); color:var(--warn); }
.badge-danger { background:var(--danger-tint); color:var(--danger); }
.badge-neutral { background:var(--sunken); color:var(--text-muted); }

.cj .btn-primary { background:var(--primary); color:var(--on-primary); }
.cj .btn-primary:hover { background:var(--primary-hover); color:var(--on-primary); }
.cj .btn-secondary { background:var(--surface); color:var(--text); border-color:var(--border-strong); }
.cj .btn-secondary:hover { border-color:var(--primary); color:var(--primary); }
.cj .btn-danger { background:var(--danger-tint); color:var(--danger); }
.cj .btn { min-height:36px; }
.cj .input, .cj select.input, .cj textarea.input { border-color:var(--border-strong); background:var(--surface); color:var(--text); }
.cj .label { color:var(--text-muted); font-size:12px; font-weight:500; }
.cj :focus-visible { outline:2px solid var(--primary); outline-offset:2px; }
.cj-video { position:relative; width:100%; aspect-ratio:16/9; border-radius:var(--radius-control); overflow:hidden; background:var(--sunken); }
.cj-video iframe, .cj-video > div { position:absolute; inset:0; width:100%; height:100%; border:0; }
.cj-pills { display:flex; gap:6px; flex-wrap:wrap; }
.cj-choice { display:flex; align-items:center; gap:8px; min-height:44px; padding:0 12px; border:1px solid var(--border-strong); border-radius:var(--radius-control); background:var(--surface); font-size:14px; font-weight:500; color:var(--text); cursor:pointer; }
.cj-choice:has(input:checked) { border:2px solid var(--primary); background:var(--primary-tint); }
/* Skill tree */
/* Achievements map: hexagon tiles (features/community/ui.py hex_map) */
.cj-mapsplit { display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); gap:var(--space-4); align-items:start; }
@media (max-width: 860px) { .cj-mapsplit { grid-template-columns:1fr; } }
.cj-legend { display:flex; flex-wrap:wrap; gap:var(--space-3); font-size:12px; color:var(--text-muted); font-weight:500; }
.cj-legend span { display:inline-flex; align-items:center; gap:6px; }
.cj-legend i { width:12px; height:12px; border-radius:2px; display:inline-block; }
.cj-legend .done { background:var(--ok-tint); border:1px solid var(--ok); }
.cj-legend .now { background:var(--surface); border:2px solid var(--primary); }
.cj-legend .next { background:var(--surface); border:1px dashed var(--border-strong); }
.cj-legend .fog { background:var(--sunken); }
.cj-hexmap { position:relative; width:100%; height:0; }
.cj-hex { position:absolute; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px; padding:0; text-align:center; text-decoration:none; color:var(--text); }
.cj-hex > span { position:relative; z-index:1; width:84%; }
.cj-hex-shape { position:absolute; left:3%; top:3%; width:94%; height:94%; overflow:visible; z-index:0; }
.cj-hex-shape polygon { fill:var(--sunken); stroke:var(--border); stroke-width:1.5; vector-effect:non-scaling-stroke; transition:stroke .15s; }
.cj-hex-name { font-size:clamp(9px, 1vw, 13px); font-weight:600; line-height:1.2; overflow-wrap:normal; }
.cj-hex-sub { font-size:clamp(9px, .95vw, 12px); color:var(--text-muted); font-weight:500; line-height:1.2; }
.cj-hex.fog polygon { stroke:transparent; }
.cj-hex.team .cj-hex-name { font-size:clamp(9px, 1.05vw, 14px); }
.cj-hex.done polygon { fill:var(--ok-tint); stroke:var(--ok); }
.cj-hex.now polygon { fill:var(--surface); stroke:var(--primary); stroke-width:3; }
.cj-hex.next polygon { fill:var(--surface); stroke:var(--border-strong); stroke-dasharray:5 4; }
.cj-hex.next .cj-hex-name { color:var(--text-muted); font-weight:500; }
.cj-hex:hover polygon, .cj-hex:focus-visible polygon { stroke:var(--primary); stroke-width:3; }
.cj-hex:focus-visible { outline:none; }
.cj-hex.sel polygon { stroke:var(--brand-deep); stroke-width:4; }
.cj-hex.sel { filter:drop-shadow(0 2px 6px rgba(0,0,0,.18)); z-index:2; }
.cj-stars { display:inline-flex; gap:2px; color:var(--border-strong); font-size:18px; line-height:1; }
.cj-stars .on, .cj-hex-stars .on { color:var(--warn); }
.cj-hex > .cj-hex-stars { display:flex; flex-wrap:wrap; justify-content:center; width:58%; color:var(--border-strong); font-size:clamp(7px, .8vw, 11px); line-height:1; letter-spacing:-.5px; }
.cj-levels { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:6px; }
.cj-levels span { text-align:center; padding:6px 0; border-radius:var(--radius-control); border:1px solid var(--border); font-size:12px; color:var(--text-muted); font-variant-numeric:tabular-nums; }
.cj-levels span.on { background:var(--warn-tint); border-color:var(--warn); color:var(--text); font-weight:600; }

.cj-tabs { display:flex; gap:4px; flex-wrap:wrap; border-bottom:1px solid var(--border); padding-bottom:var(--space-2); }
.cj-tab { padding:8px 12px; border-radius:var(--radius-control); font-size:14px; font-weight:500; color:var(--text-muted); text-decoration:none; }
.cj-tab:hover { color:var(--primary); }
.cj-tab.on { background:var(--primary-tint); color:var(--primary); }
.cj-table { width:100%; border-collapse:collapse; font-size:14px; }
.cj-table th { text-align:left; font-size:12px; font-weight:500; color:var(--text-muted); background:var(--sunken); padding:8px 12px; white-space:nowrap; }
.cj-table td { padding:10px 12px; border-top:1px solid var(--border); vertical-align:top; color:var(--text); }
.cj-table td.n, .cj-table th.n { text-align:right; font-variant-numeric:tabular-nums; }
.cj-table tr.sel td { background:var(--primary-tint); }
.cj-tablewrap { overflow-x:auto; border:1px solid var(--border); border-radius:var(--radius-card); background:var(--surface); }
.cj-split { display:flex; gap:var(--space-4); flex-wrap:wrap; align-items:flex-start; }
.cj-split > .wide { flex:999 1 560px; min-width:0; }
.cj-split > .side { flex:1 1 320px; min-width:0; }
.cj-dl { display:grid; grid-template-columns:max-content 1fr; gap:6px 12px; font-size:14px; }
.cj-dl dt { color:var(--text-muted); font-size:12px; font-weight:500; padding-top:2px; }
.cj-dl dd { margin:0; color:var(--text); overflow-wrap:anywhere; }
.cj-locked { display:flex; align-items:center; justify-content:space-between; gap:8px; min-height:44px; padding:0 12px; border-radius:var(--radius-control); border:1px dashed var(--border-strong); background:var(--sunken); color:var(--text-muted); font-size:14px; font-weight:500; text-decoration:none; }
/* ── Platform-brief layer: graphic, playful, picture first ─────────────
   Page heads with an audience icon tile, gradient heroes with "pieces",
   device icon tiles, "+" disclosures and quiet row menus. Tokens only. */
.ph { display:flex; align-items:center; gap:16px; margin-bottom:24px; flex-wrap:wrap; }
.ph-ico { width:52px; height:52px; border-radius:16px; display:grid; place-items:center; flex-shrink:0; color:#fff; background:var(--primary); box-shadow:0 6px 16px -8px var(--primary); }
.ph-ico svg { width:26px; height:26px; }
.ph-ico.t-eng { background:var(--accent); box-shadow:0 6px 16px -8px var(--accent); }
.ph-ico.t-lead { background:var(--lead); box-shadow:0 6px 16px -8px var(--lead); }
.ph-ico.t-brand { background:var(--gradient-brand); box-shadow:0 6px 16px -8px var(--brand-deep); }
.ph-ico.t-danger { background:var(--danger); box-shadow:0 6px 16px -8px var(--danger); }
:root[data-theme="dark"] .ph-ico:not(.t-brand) { color:var(--bg); }
.ph-text { flex:1 1 260px; min-width:0; display:flex; flex-direction:column; gap:4px; }
.ph-text p { margin:0; color:var(--text-muted); font-size:.95rem; max-width:70ch; }
.ph-acts { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
@media (max-width:640px){ .ph { gap:12px; } .ph-ico { width:44px; height:44px; border-radius:12px; } .ph-ico svg { width:22px; height:22px; } .ph-acts { width:100%; } }

/* Gradient hero with clickable "pieces" (dashboard, home). */
.hero { background:var(--gradient-brand); color:var(--on-brand); border-radius:var(--radius-panel); padding:28px; margin-bottom:20px; position:relative; overflow:hidden; display:grid; gap:20px; }
.hero::after { content:""; position:absolute; right:-24px; top:-24px; width:220px; height:220px; background:url(/static/brand/fixmymedtech-africa-white.png) center/contain no-repeat; opacity:.16; pointer-events:none; }
.hero > * { position:relative; z-index:1; }
.hero-top { display:flex; gap:16px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; }
.hero .eyebrow, .hero-eyebrow { font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--on-brand); opacity:.85; }
.hero h1 { color:var(--on-brand); font-size:clamp(1.6rem, 3.4vw, 2.4rem); line-height:1.08; margin-top:4px; }
.hero p { color:var(--on-brand); opacity:.92; font-size:1rem; margin-top:6px; max-width:56ch; }
.hero .btn-light { background:var(--on-brand); color:var(--brand-deep); font-weight:700; box-shadow:0 6px 18px -8px rgba(0,0,0,.4); }
.hero .btn-light:hover { transform:translateY(-1px); }
.pieces { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:10px; }
.piece { background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.28); border-radius:14px; padding:14px; color:var(--on-brand); text-decoration:none; display:flex; flex-direction:column; gap:6px; transition:transform .15s, background .15s; min-width:0; }
.piece:hover { background:rgba(255,255,255,.2); transform:translateY(-2px); color:var(--on-brand); }
.piece-top { display:flex; align-items:center; gap:8px; }
.piece .dot { width:28px; height:28px; border-radius:50%; background:var(--on-brand); display:grid; place-items:center; color:var(--brand-deep); flex-shrink:0; }
.piece .dot svg { width:16px; height:16px; }
.piece .dot.ok { color:var(--ok); } .piece .dot.warn { color:var(--warn); } .piece .dot.danger { color:var(--danger); }
.piece b { font-size:28px; line-height:1; font-weight:800; font-variant-numeric:tabular-nums; letter-spacing:-.02em; }
.piece small { font-size:12px; opacity:.9; line-height:1.3; font-weight:600; }
.meter { height:8px; border-radius:999px; background:rgba(255,255,255,.25); overflow:hidden; }
.meter > span { display:block; height:100%; background:var(--on-brand); border-radius:999px; }
@media (max-width:640px){ .hero { padding:20px; border-radius:var(--radius-card); } .pieces { grid-template-columns:1fr 1fr; } }

.hero .btn-ghost-light { background:transparent; color:var(--on-brand); border-color:rgba(255,255,255,.6); }
.hero .btn-ghost-light:hover { background:rgba(255,255,255,.14); color:var(--on-brand); }
.big-tiles { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; }
.big-tile { display:flex; flex-direction:column; align-items:flex-start; gap:14px; padding:18px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-card); color:var(--text); text-decoration:none; box-shadow:var(--shadow-card); transition:transform .15s, border-color .15s, box-shadow .15s; }
.big-tile:hover { transform:translateY(-2px); border-color:var(--primary); box-shadow:var(--shadow-float); color:var(--text); }
.big-tile b { font-size:1rem; }
@media (prefers-reduced-motion: reduce) { .big-tile { transition:none; } .big-tile:hover { transform:none; } }

/* Section head inside a card: icon dot + title + side link. */
.sec-h { display:flex; align-items:center; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
.sec-h h2 { font-size:1.25rem; margin:0; }
.sec-h .side { margin-left:auto; font-size:14px; font-weight:600; }
.sec-ico { width:32px; height:32px; border-radius:10px; display:grid; place-items:center; background:var(--primary-tint); color:var(--primary); flex-shrink:0; }
.sec-ico svg { width:18px; height:18px; }
.sec-ico.danger { background:var(--danger-tint); color:var(--danger); }
.sec-ico.ok { background:var(--ok-tint); color:var(--ok); }
.sec-ico.eng { background:var(--accent-tint); color:var(--accent); }
.sec-ico.lead { background:var(--lead-tint); color:var(--lead); }

/* Device icon tile (category picture instead of an emoji or a letter). */
.dthumb { width:44px; height:44px; border-radius:12px; display:grid; place-items:center; background:var(--primary-tint); color:var(--primary); flex-shrink:0; }
.dthumb svg { width:24px; height:24px; }
.dthumb.lg { width:88px; height:88px; border-radius:var(--radius-card); }
.dthumb.lg svg { width:44px; height:44px; }
.dthumb.is-ok { background:var(--ok-tint); color:var(--ok); }
.dthumb.is-warn { background:var(--warn-tint); color:var(--warn); }
.dthumb.is-danger { background:var(--danger-tint); color:var(--danger); }
.dthumb.is-neutral { background:var(--sunken); color:var(--text-muted); }
.dname { display:flex; align-items:center; gap:12px; min-width:0; color:var(--text); text-decoration:none; }
.dname:hover b { color:var(--primary); }
.dname > div > b { display:block; font-size:.9rem; font-weight:600; color:var(--text); overflow-wrap:anywhere; }
.dname > div > span { display:block; font-size:.75rem; color:var(--text-muted); }

/* "+" disclosure (platform brief build-notes style), for any details.fold. */
details.fold { border:1px solid var(--border); border-radius:var(--radius-card); background:var(--surface); margin-bottom:16px; }
details.fold > summary { cursor:pointer; list-style:none; display:flex; align-items:center; gap:10px; padding:12px 16px; font-weight:700; font-size:14px; color:var(--primary); }
details.fold > summary::-webkit-details-marker { display:none; }
details.fold > summary::before { content:"+"; width:22px; height:22px; border-radius:7px; background:var(--primary-tint); display:grid; place-items:center; font-size:16px; flex-shrink:0; }
details.fold[open] > summary::before { content:"\2013"; }
details.fold > summary .hint { margin-left:auto; font-weight:500; font-size:12px; color:var(--text-muted); }
.fold-body { padding:0 16px 16px; }

/* Quiet row menu: secondary actions behind "⋯". */
details.rowmenu { position:relative; display:inline-block; }
details.rowmenu > summary { list-style:none; cursor:pointer; width:34px; height:34px; border-radius:10px; display:grid; place-items:center; color:var(--text-muted); border:1px solid transparent; }
details.rowmenu > summary::-webkit-details-marker { display:none; }
details.rowmenu > summary:hover, details.rowmenu[open] > summary { background:var(--sunken); color:var(--text); border-color:var(--border); }
details.rowmenu > summary svg { width:18px; height:18px; }
.rowmenu-pop { position:absolute; right:0; top:calc(100% + 6px); z-index:50; min-width:160px; padding:6px; display:flex; flex-direction:column; gap:2px; background:var(--surface); border:1px solid var(--border); border-radius:12px; box-shadow:var(--shadow-float); }
.rowmenu-pop a, .rowmenu-pop button { all:unset; box-sizing:border-box; cursor:pointer; padding:8px 12px; border-radius:8px; font-size:.875rem; font-weight:500; color:var(--text); }
.rowmenu-pop a:hover, .rowmenu-pop button:hover { background:var(--sunken); }
.rowmenu-pop .danger { color:var(--danger); }
.rowmenu-pop .danger:hover { background:var(--danger-tint); }

/* Friendly empty state: a big icon circle, one line, one action. */
.empty { display:flex; flex-direction:column; align-items:center; text-align:center; gap:10px; padding:36px 16px; border:2px dashed var(--border); border-radius:var(--radius-panel); color:var(--text-muted); }
.empty-ico { width:64px; height:64px; border-radius:50%; display:grid; place-items:center; background:var(--primary-tint); color:var(--primary); }
.empty-ico svg { width:30px; height:30px; }
.empty b { color:var(--text); font-size:1rem; }

/* Public QR page, brief layout: identity, two big actions, three tiles,
   everything else folded under "More details". */
.pub-ident { display:flex; gap:14px; align-items:flex-start; padding:18px 16px; background:var(--surface); border-bottom:1px solid var(--border); }
.pub-ident .dev-name { font-size:1.35rem; line-height:1.2; margin:2px 0 4px; letter-spacing:-.01em; }
.pub-ident .grow { flex:1; min-width:0; }
.pub-acts { display:grid; gap:10px; padding:16px; }
.pub-acts .btn { width:100%; padding:13px 16px; font-size:1rem; font-weight:700; border-radius:12px; }
.pub-acts .btn svg { width:18px; height:18px; }
.mini-tiles { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:8px; padding:0 16px 16px; }
.mini-tile { background:var(--surface); border:1px solid var(--border); border-top:3px solid var(--border-strong); border-radius:12px; padding:10px 8px; text-align:center; text-decoration:none; color:var(--text); display:flex; flex-direction:column; gap:2px; min-width:0; }
.mini-tile:hover { border-color:var(--primary); }
.mini-tile b { font-size:1.15rem; line-height:1.2; font-weight:800; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }
.mini-tile span { font-size:11px; color:var(--text-muted); font-weight:600; line-height:1.25; }
.mini-tile.is-ok { border-top-color:var(--ok); } .mini-tile.is-warn { border-top-color:var(--warn); } .mini-tile.is-danger { border-top-color:var(--danger); }
.mini-tile.is-warn b { color:var(--warn); } .mini-tile.is-danger b { color:var(--danger); }
.pub-page details.fold { margin:0 16px 16px; }
.pub-page .fold-body .pub-section { padding:12px 0; border-top:1px solid var(--border); }
.pub-page .fold-body .info-list { padding:0; }

@media (prefers-reduced-motion: reduce) { .piece, .nav-ico, .net-card { transition:none; } .piece:hover, .nav-link:hover .nav-ico { transform:none; } }

@media (max-width: 760px) {
  .cj-card { padding:var(--space-4); }
  .cj-hero { padding:var(--space-4); }
  .cj .form-row { grid-template-columns:1fr; }
}
"""


def status_badge(status: str, type: str = "device", lang: str = "en"):
    _ = make_t(lang)
    m = {
        "device": {
            "operational":    (_("badge.operational"),     "badge-ok"),
            "maintenance":    (_("badge.maintenance"),     "badge-warn"),
            "fault":          (_("badge.fault"),           "badge-danger"),
            "decommissioned": (_("badge.decommissioned"),  "badge-neutral"),
        },
        "fault": {
            "open":        (_("badge.open"),        "badge-danger"),
            "assigned":    (_("badge.assigned"),    "badge-warn"),
            "diagnosed":   (_("badge.diagnosed"),   "badge-warn"),
            "approved":    (_("badge.approved"),    "badge-warn"),
            "in_progress": (_("badge.in_progress"), "badge-warn"),
            "resolved":    (_("badge.resolved"),    "badge-ok"),
        },
        "severity": {
            "low":      (_("badge.low"),      "badge-neutral"),
            "medium":   (_("badge.medium"),   "badge-warn"),
            "high":     (_("badge.high"),     "badge-danger"),
            "critical": (_("badge.critical"), "badge-danger"),
        },
        "log": {
            "open":        (_("badge.open"),        "badge-danger"),
            "in_progress": (_("badge.in_progress"), "badge-warn"),
            "closed":      (_("badge.closed"),      "badge-ok"),
        },
        # Onboarding (design system: ok = done, warn = someone is on it,
        # neutral = not in play).
        "quest": {
            "done": (_("ob.badge_done"),  "badge-ok"),
            "todo": (_("ob.badge_todo"),  "badge-neutral"),
        },
        "engineer": {
            "can_register":   (_("ob.badge_can_register"),   "badge-ok"),
            "waiting_quests": (_("ob.badge_waiting_quests"), "badge-warn"),
            "waiting_talk":   (_("ob.badge_waiting_talk"),   "badge-warn"),
            "not_now":        (_("ob.badge_not_now"),        "badge-neutral"),
        },
        "invitation": {
            "sent":            (_("ob.badge_sent"),            "badge-warn"),
            "account_created": (_("ob.badge_account_created"), "badge-warn"),
            "clinic_ready":    (_("ob.badge_clinic_ready"),    "badge-warn"),
            "confirmed":       (_("ob.badge_confirmed"),       "badge-ok"),
            "not_now":         (_("ob.badge_not_now"),         "badge-neutral"),
            "cancelled":       (_("ob.badge_cancelled"),       "badge-neutral"),
        },
        "clinic": {
            "active":       (_("ob.badge_clinic_active"),       "badge-ok"),
            "talk_pending": (_("ob.badge_clinic_talk_pending"), "badge-warn"),
        },
    }
    label, cls = m.get(type, m["device"]).get(status, (status, "badge-neutral"))
    return Span(label, cls=f"badge {cls}")


def stats_section(stats, _, style="max-width:720px;margin-top:20px;"):
    """The four activity counters.

    One component shared by My Profile and a member's public page, so the
    numbers a person sees on their own profile are by construction the same
    ones everyone else sees — and the same four the Network table sorts by.
    """
    stats = stats or {}

    def tile(label_key, key, accent=""):
        return Div(
            Div(_(label_key), cls="stat-label"),
            Div(str(stats.get(key, 0)), cls="stat-num"),
            cls=("stat-card " + accent).strip(),
        )

    return Div(
        H3(_("profile.stats_heading"), cls="card-title"),
        Div(
            tile("profile.stats_devices", "devices_registered"),
            tile("profile.stats_faults_resolved", "faults_resolved", "g"),
            tile("profile.stats_maint_performed", "maintenance_performed", "a"),
            tile("profile.stats_invites", "invites", "p"),
            cls="stat-grid",
        ),
        cls="card",
        style=style,
    )


# ── Lucide icons ────────────────────────────────────────────────────────────
# Inline 24×24 stroke icons (stroke=currentColor) so they inherit link colour
# and stay crisp in both themes.
LUCIDE_ICONS = {
    "board":     '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "inbox": '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
             '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    "journey": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    "hexagon": '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    "library": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    "home": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>'
            '<path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/>'
                '<rect width="7" height="5" x="14" y="3" rx="1"/>'
                '<rect width="7" height="9" x="14" y="12" rx="1"/>'
                '<rect width="7" height="5" x="3" y="16" rx="1"/>',
    "devices": '<rect width="20" height="14" x="2" y="3" rx="2"/>'
               '<line x1="8" x2="16" y1="21" y2="21"/>'
               '<line x1="12" x2="12" y1="17" y2="21"/>',
    "faults": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
              '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "tasks": '<rect width="8" height="4" x="8" y="2" rx="1"/>'
             '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
             '<path d="M12 11h4"/><path d="M12 16h4"/>'
             '<path d="M8 11h.01"/><path d="M8 16h.01"/>',
    "groups": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>'
              '<path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/>'
              '<path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/>'
              '<path d="M10 6h4"/><path d="M10 10h4"/>'
              '<path d="M10 14h4"/><path d="M10 18h4"/>',
    "profile": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>'
               '<circle cx="12" cy="7" r="4"/>',
    # Lucide graph-star: a hub with satellites, rather than the people glyph.
    "network": '<path d="m12.342 9.316 1.764-3.527"/>'
               '<path d="m12.59 14.545 2.35 3.759"/>'
               '<path d="m13.982 12.332 4.03.447"/>'
               '<path d="M5.414 17.586 8.88 14.12"/>'
               '<path d="M9.025 9.742 5.317 5.505"/>'
               '<circle cx="11" cy="12" r="3"/>'
               '<circle cx="15" cy="4" r="2"/>'
               '<circle cx="16" cy="20" r="2"/>'
               '<circle cx="20" cy="13" r="2"/>'
               '<circle cx="4" cy="19" r="2"/>'
               '<circle cx="4" cy="4" r="2"/>',
    "logout": '<path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>'
              '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>',
    # Onboarding: Getting started, Invite a clinic, Talk host.
    "flag": '<path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/>'
            '<path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7"/>',
    "mic": '<path d="M12 19v3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/>'
           '<rect x="9" y="2" width="6" height="13" rx="3"/>',
    # Redesign: page heads, hero pieces and device category pictures.
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "wind": '<path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/>'
            '<path d="M12.6 19.4A2 2 0 1 0 14 16H2"/>',
    "droplet": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/>'
            '<path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "stethoscope": '<path d="M11 2v2"/><path d="M5 2v2"/><path d="M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1"/>'
                   '<path d="M8 15a6 6 0 0 0 12 0v-3"/><circle cx="20" cy="10" r="2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/>'
           '<path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    "bed": '<path d="M2 4v16"/><path d="M2 8h18a2 2 0 0 1 2 2v10"/><path d="M2 17h20"/><path d="M6 8v9"/>',
    "weight": '<circle cx="12" cy="5" r="3"/><path d="M6.5 8a2 2 0 0 0-1.905 1.46L2.1 18.5A2 2 0 0 0 4 21h16a2 2 0 0 0 1.925-2.54L19.4 9.5A2 2 0 0 0 17.48 8Z"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "more": '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "qr": '<rect width="5" height="5" x="3" y="3" rx="1"/><rect width="5" height="5" x="16" y="3" rx="1"/>'
          '<rect width="5" height="5" x="3" y="16" rx="1"/><path d="M21 16h-3a2 2 0 0 0-2 2v3"/><path d="M21 21v.01"/>'
          '<path d="M12 7v3a2 2 0 0 1-2 2H7"/><path d="M3 12h.01"/><path d="M12 3h.01"/><path d="M12 16v.01"/>'
          '<path d="M16 12h1"/><path d="M21 12v.01"/><path d="M12 21v-1"/>',
    "clipboard": '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
                 '<path d="m9 14 2 2 4-4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
}

# Device category slug → picture (lucide name). Replaces the emoji stored on
# the category row: the design system has no emoji in the product.
CATEGORY_ICONS = {
    "ventilator": "wind", "anaesthetic_machine": "wind", "oxygen_concentrator": "wind",
    "nebulizer": "wind", "oxygen_cylinder_flowmeter": "gauge", "suction_machine": "wind",
    "defibrillator": "zap", "electrosurgical_unit": "zap",
    "infusion_pump": "droplet", "infant_incubator": "heart",
    "autoclave_sterilizer": "flame", "xray_machine": "scan", "ultrasound_machine": "scan",
    "endoscope": "scan", "ecg_machine": "activity", "pulse_oximeter": "activity",
    "electronic_diagnostic_equipment": "activity", "sphygmomanometer": "gauge",
    "scale": "weight", "lamp": "sun", "operating_table": "bed", "stethoscope": "stethoscope",
}


def device_icon(category, tone: str = "", size: str = ""):
    """A rounded tile with the device category's picture. `category` is the
    category dict or its slug; `tone` (ok/warn/danger/neutral) tints it with
    the status colour, `size="lg"` for the device ID card."""
    slug = category.get("slug") if isinstance(category, dict) else category
    cls = " ".join(c for c in ("dthumb", size, f"is-{tone}" if tone else "") if c)
    return Span(lucide(CATEGORY_ICONS.get(slug or "", "devices")), cls=cls, aria_hidden="true")


def page_head(title, sub="", icon: str = "", tone: str = "", *actions):
    """Page title row (platform brief chapter head): an icon tile in the
    audience colour (""=clinic blue, "eng" teal, "lead" purple, "brand"
    gradient, "danger"), the title, one line under it, actions on the right."""
    return Div(
        Span(lucide(icon), cls=f"ph-ico t-{tone}" if tone else "ph-ico", aria_hidden="true") if icon else "",
        Div(H1(title), (P(sub) if isinstance(sub, str) else sub) if sub else "", cls="ph-text"),
        Div(*actions, cls="ph-acts") if actions else "",
        cls="page-header ph",
    )


def lucide(name: str, cls: str = ""):
    """Return an inline Lucide SVG icon (falls back to an empty string)."""
    body = LUCIDE_ICONS.get(name)
    if not body:
        return ""
    return Safe(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true"'
        + (f' class="{cls}"' if cls else "")
        + f">{body}</svg>"
    )


# Permissions that open the community admin dashboard (utils/community.py).
DASHBOARD_PERMISSIONS = ("view_applicants", "view_members", "view_history")


# ── Three worlds (platform brief) ───────────────────────────
# Equipment = the clinic CMMS (primary blue), Work = the engineer's workspace
# (teal), Community = journey, teams, recognition, library (lead purple).
# The brand bar switches world, the sidebar lists only the current world's
# pages. Which world a page belongs to comes from its path; pages outside
# every world (profile, home) keep the world you came from.
WORLD_TONES = {"equipment": "", "work": "eng", "community": "lead"}
WORLD_ICONS = {"equipment": "devices", "work": "wrench", "community": "journey"}
WORLD_PATHS = (
    ("work", ("/tasks", "/requests", "/invite-clinic", "/host", "/getting-started")),
    ("community", ("/community", "/lead", "/network")),
    ("equipment", ("/dashboard", "/devices", "/device", "/new_device", "/faults",
                   "/groups", "/library", "/documents", "/calls", "/clinic", "/d/", "/scan-result")),
)


def world_for_path(path: str) -> str:
    """The world a path belongs to, or "" (profile, home, feedback...)."""
    for world, prefixes in WORLD_PATHS:
        for pre in prefixes:
            if path == pre or path.startswith(pre if pre.endswith("/") else pre + "/"):
                return world
    return ""


def user_worlds(lang: str = "en", user: dict | None = None) -> list[dict]:
    """The worlds this account has unlocked, each with its sidebar links:
    [{"key", "tone", "icon", "label", "href", "links": [(href, icon, label)]}].
    Guardrail "show less, unlock more": a new engineer (welcome quests not
    done) has the community only; a clinic account has its equipment only
    (with the library and the people directory); an engineer whose quests are
    done has all three."""
    _ = make_t(lang)
    user = user if user is not None else current_user_ctx()
    status = user.get("member_status") or "member"
    perms = set(user.get("permissions") or [])
    engineer = (user.get("account_kind") or "engineer") == "engineer"

    def world(key, links):
        return {"key": key, "tone": WORLD_TONES[key], "icon": WORLD_ICONS[key],
                "label": _(f"nav.world_{key}"), "href": links[0][0], "links": links}

    if status in ("applicant", "refused"):
        return [world("community", [
            ("/community/start", "journey", _("nav.community_start")),
            ("/library",         "library", _("nav.library")),
        ])]

    equipment = [
        ("/dashboard", "dashboard", _("nav.dashboard")),
        ("/devices",   "devices",   _("nav.devices")),
        ("/faults",    "faults",    _("nav.faults")),
        ("/groups",    "groups",    _("nav.groups")),
        ("/library",   "library",   _("nav.library")),
    ]
    leader = [("/lead", "check", _("nav.lead"))] if any(p.startswith("recognise:") for p in perms) else []
    admin = [("/community/admin", "shield", _("nav.community_admin"))] if perms & set(DASHBOARD_PERMISSIONS) else []
    host = [("/host", "mic", _("nav.talk_host"))] if user.get("is_talk_host") else []

    if not engineer:
        # Clinic accounts and clinic staff are not community members: one
        # world, plus the manuals and the people directory they still need.
        return [world("equipment", equipment + [
            ("/tasks",   "tasks",   _("nav.tasks")),
            ("/network", "network", _("nav.network")),
        ] + host + leader + admin)]

    work = [
        ("/tasks",        "tasks", _("nav.tasks")),
        ("/requests",     "inbox", _("nav.requests")),
        # Getting started is done (member): the invite page is the next step.
        ("/invite-clinic", "mail", _("nav.invite_clinic")),
    ] + host
    community = [
        ("/community",              "journey", _("nav.community")),
        ("/community/achievements", "hexagon", _("nav.community_achievements")),
        ("/network",                "network", _("nav.network")),
        ("/community/tasks",        "board",   _("nav.task_board")),
    ] + leader + admin
    return [world("equipment", equipment), world("work", work), world("community", community)]


def current_world(worlds: list[dict], user: dict | None = None) -> dict:
    user = user if user is not None else current_user_ctx()
    want = user.get("world") or ""
    for w in worlds:
        if w["key"] == want:
            return w
    return worlds[0]


def world_switcher(lang: str = "en", where: str = "top"):
    """The world tabs: in the brand bar on wide screens (where="top"), a
    bottom tab bar on phones (where="bottom"). Hidden while the account has
    a single world."""
    _ = make_t(lang)
    worlds = user_worlds(lang)
    if len(worlds) < 2:
        return ""
    cur = current_world(worlds)["key"]
    tabs = [A(Span(lucide(w["icon"]), cls="wt-ico"), Span(w["label"], cls="wt-label"),
              href=w["href"], cls=" ".join(c for c in ("wt", f"w-{w['key']}",
                                                         "on" if w["key"] == cur else "") if c),
              aria_current="page" if w["key"] == cur else None)
            for w in worlds]
    return Nav(*tabs, cls=f"worlds worlds-{where}", aria_label=_("nav.worlds_label"))


def sidebar(current: str = "", lang: str = "en"):
    worlds = user_worlds(lang)
    world = current_world(worlds)
    # One world at a time: no section headings, the tone is the world's.
    sections = [("", world["tone"], world["links"])]
    nav_items = []
    for heading, tone, links in sections:
        if not links:
            continue
        if heading:
            nav_items.append(Div(heading, cls="nav-sec"))
        for href, icon, label in links:
            nav_items.append(A(
                Span(lucide(icon), cls="nav-ico"), Span(label, cls="nav-label"),
                href=href, title=label,
                cls=" ".join(c for c in ("nav-link", f"t-{tone}" if tone else "",
                                         "active" if current == href else "") if c)))
    return Aside(
        Div(
            A(
                # Design system: the name is always the logo image, never retyped.
                Img(src="/static/fixmymedtech_logo.png", cls="brand-logo", alt="FixMyMedTech"),
                href="/home",
                title="FixMyMedTech",
            ),
            Button("✕", id="sb-close", cls="sb-close", aria_label="Close menu",
                   onclick="toggleSidebar(false)"),
            cls="sb-head"
        ),
        Nav(
            *nav_items,
            cls="sb-nav"
        ),
        Div(
            language_switcher(lang),
            theme_toggle(),
            cls="sb-foot"
        ),
        cls="sidebar",
        id="app-sidebar"
    )


def language_switcher(current_lang: str):
    options = []
    for code, name in LANGUAGES.items():
        options.append(Option(code.upper(), value=code, selected=(code == current_lang)))
    return Form(
        Select(*options, name="lang", cls="input-lang",
               onchange="this.form.submit()"),
        method="post", action="/lang",
        style="display:flex;align-items:center;gap:6px;"
    )


def feedback_widget(lang: str = "en"):
    """Floating "?" button (bottom-right) opening a menu to send feedback or
    report an issue. Rendered by every shell, so it is on every page."""
    _ = make_t(lang)
    return Div(
        Div(
            A("💬 ", _("feedback.menu_feedback"), href="/feedback?type=feedback", data_type="feedback"),
            A("🐞 ", _("feedback.menu_issue"), href="/feedback?type=issue", data_type="issue"),
            id="fb-menu", cls="fb-menu",
        ),
        Button("?", id="fb-btn", type="button", cls="fb-btn",
               title=_("feedback.button_label"), aria_label=_("feedback.button_label"),
               aria_expanded="false", aria_controls="fb-menu",
               onclick="toggleFeedbackMenu()"),
        id="fb-widget", cls="fb-widget",
    )


def theme_toggle():
    return Button("☾", id="theme-toggle", cls="theme-btn",
                  aria_label="Toggle dark mode", onclick="toggleTheme()")


def avatar_menu(lang: str = "en"):
    _ = make_t(lang)
    user = current_user_ctx()
    name = user.get("name") or ""
    username = user.get("username") or ""
    email = user.get("email") or ""

    # Always point at /profile/photo, which serves the *current* avatar from
    # the backend (ignoring any cached session value), so a photo uploaded
    # from another device shows up here. If the user has no avatar, the
    # onerror fallback swaps in the "◉" placeholder.
    btn_content = Img(
        src="/profile/photo",
        alt=name or "◉",
        style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;",
        onerror="this.onerror=null;this.outerHTML='\u25c9';",
    )
    second_row = username or email

    return Div(
        Button(btn_content, id="avatar-btn", cls="avatar-btn", aria_label="Account menu",
               style="overflow:hidden;padding:0;",
               onclick="toggleAvatarMenu()"),
        Div(
            Div(
                Div(name or _("profile.me_heading"), cls="avatar-menu-name"),
                Div(second_row, cls="avatar-menu-email"),
                cls="avatar-menu-user",
            ),
            A(Span(lucide("profile"), cls="nav-menu-ico"), _("nav.profile"), href="/profile"),
            A(Span(lucide("logout"), cls="nav-menu-ico"), _("nav.logout"), href="/logout"),
            Div(
                Div(_("lang.label"),
                    style="font-size:.7rem;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.04em;margin:4px 12px;"),
                language_switcher(lang),
                style="border-top:1px solid var(--c-border);padding-top:8px;margin-top:6px;"
            ),
            id="avatar-menu", cls="avatar-menu",
        ),
        cls="avatar-wrap",
    )


SHELL_SCRIPT = """
function theme(){
  var s = localStorage.getItem('fmm-theme');
  if (s) return s;
  try {
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  } catch (e) { return 'light'; }
}
function applyTheme(mode){
  document.documentElement.setAttribute('data-theme', mode);
  var b = document.getElementById('theme-toggle');
  if (b) b.textContent = (mode === 'dark') ? '\u2600' : '\u263E';
}
function toggleTheme(){
  var next = theme() === 'dark' ? 'light' : 'dark';
  localStorage.setItem('fmm-theme', next);
  applyTheme(next);
}
function initTheme(){
  var s = localStorage.getItem('fmm-theme');
  applyTheme(s ? s : theme());
}
function toggleSidebar(open){
  var sb = document.getElementById('app-sidebar');
  if (!sb) return;
  var drawer = window.innerWidth <= 768;
  var isOpen = (typeof open === 'boolean') ? open
    : (drawer ? !sb.classList.contains('open')
              : !document.body.classList.contains('sidebar-collapsed'));
  if (drawer) {
    sb.classList.toggle('open', isOpen);
    var bd = document.getElementById('sb-backdrop');
    if (bd) bd.classList.toggle('show', isOpen);
  } else {
    document.body.classList.toggle('sidebar-collapsed', isOpen);
    localStorage.setItem('fmm-collapsed', isOpen ? '1' : '0');
  }
}
function toggleAvatarMenu(open){
  var m = document.getElementById('avatar-menu');
  if (!m) return;
  var isOpen = (typeof open === 'boolean') ? open : !m.classList.contains('open');
  m.classList.toggle('open', isOpen);
}
function initSidebar(){
  if (window.innerWidth > 768 && localStorage.getItem('fmm-collapsed') === '1') {
    document.body.classList.add('sidebar-collapsed');
  }
}
/* Shared client-side image compression (keeps uploads under nginx 1MB limit).
   Returns a Promise resolving to a JPEG Blob. Falls back to smaller size /
   lower quality until the result is under ~900KB. */
function fmmCompressImage(file, maxSize, quality){
  return new Promise(function (resolve, reject) {
    var img = new Image();
    var url = URL.createObjectURL(file);
    img.onload = function () {
      var target = 900 * 1024;
      function attempt(size, q){
        var scale = Math.min(1, size / Math.max(img.width, img.height));
        var w = Math.max(1, Math.round(img.width * scale));
        var h = Math.max(1, Math.round(img.height * scale));
        var canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        canvas.toBlob(function (blob) {
          if (!blob) { reject(new Error('compress failed')); return; }
          if (blob.size > target && (size > 320 || q > 0.5)) {
            attempt(Math.round(size * 0.75), Math.max(0.45, q - 0.12));
          } else {
            resolve(blob);
          }
        }, 'image/jpeg', q);
      }
      attempt(maxSize, quality);
    };
    img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('load failed')); };
    img.src = url;
  });
}
function fmmSetFiles(input, blob, filename){
  try {
    var dt = new DataTransfer();
    dt.items.add(new File([blob], filename, { type: 'image/jpeg' }));
    input.files = dt.files;
  } catch (e) { /* leave original file if unsupported */ }
}
document.addEventListener('click', function(e){
  var wrap = document.getElementById('avatar-wrap');
  var menu = document.getElementById('avatar-menu');
  if (wrap && menu && menu.classList.contains('open') && !wrap.contains(e.target)) {
    menu.classList.remove('open');
  }
});
function toggleFeedbackMenu(open){
  var m = document.getElementById('fb-menu');
  var b = document.getElementById('fb-btn');
  if (!m) return;
  var isOpen = (typeof open === 'boolean') ? open : !m.classList.contains('open');
  if (isOpen) {
    // Tell the form which page the report is about.
    var here = encodeURIComponent(location.pathname + location.search);
    m.querySelectorAll('a[data-type]').forEach(function(a){
      a.href = '/feedback?type=' + a.getAttribute('data-type') + '&page=' + here;
    });
  }
  m.classList.toggle('open', isOpen);
  if (b) b.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}
document.addEventListener('click', function(e){
  var w = document.getElementById('fb-widget');
  if (w && !w.contains(e.target)) toggleFeedbackMenu(false);
});
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') toggleFeedbackMenu(false);
});
initTheme();
initSidebar();
"""


def is_authenticated() -> bool:
    """True when the current request carries a logged-in session."""
    u = current_user_ctx()
    return bool(u.get("name") or u.get("username") or u.get("email"))


def topbar(authenticated: bool, current: str = "", lang: str = "en"):
    _ = make_t(lang)
    authenticated = authenticated or is_authenticated()
    left = []
    if authenticated:
        left.append(Button("☰", id="sb-toggle", cls="togg-btn", aria_label="Toggle sidebar",
                           onclick="toggleSidebar()"))
    right = []
    if authenticated:
        right.append(avatar_menu(lang))
    else:
        right = [A(_("nav.library"), href="/library", cls="btn btn-secondary btn-sm"),
                 A(_("login.signin"), href="/login",
                    cls="btn btn-secondary btn-sm"),
                    language_switcher(lang)]
    return Header(
        *left,
        A(
            # Brand bar: the white mark on brand-deep (design system: white
            # rendering on dark grounds).
            Img(src="/static/brand/fixmymedtech-mark-white.png", cls="brand-logo", alt=""),
            Span("FixMyMedTech", cls="brand"),
            href="/home" if authenticated else "/",
            title="FixMyMedTech",
            cls="brand"
        ),
        world_switcher(lang, "top") if authenticated else "",
        Div(*right, cls="top-right"),
        cls="topbar"
    )


def shell(content, title: str = "FixMyMedTech", lang: str = "en",
          authenticated: bool = False, current: str = ""):
    authenticated = authenticated or is_authenticated()
    if authenticated:
        body_inner = Div(
            Div(id="sb-backdrop", cls="sb-backdrop", onclick="toggleSidebar(false)"),
            Div(
                sidebar(current, lang),
                Main(content, cls="main"),
                cls="shell"
            ),
            world_switcher(lang, "bottom"),
        )
    else:
        body_inner = Div(content, cls="shell public-shell")

    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),
            *brand_head(),
            *posthog_head(),
            Style(CSS),
        ),
        Body(
            Div(
                topbar(authenticated, current, lang),
                body_inner,
            ),
            feedback_widget(lang),
            Script(SHELL_SCRIPT)
        )
    )


def page_shell(content, current: str = "", title: str = "FixMyMedTech",
               lang: str = "en"):
    return shell(content, title=title, lang=lang, authenticated=True, current=current)


def pub_shell(content, title: str = "FixMyMedTech", lang: str = "en"):
    """Public shell (QR pages, home) — full top bar + sidebar; avatar only when
    signed in, otherwise a Sign-in button."""
    return shell(content, title=title, lang=lang, authenticated=False)


def auth_shell(content, title: str = "FixMyMedTech", lang: str = "en"):
    """Shell for login/signup/reset — standalone, no top bar."""
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),
            *brand_head(),
            *posthog_head(),
            Style(CSS),
        ),
        Body(
            Div(
                Div(language_switcher(lang), cls="lang-fab"),
                Button("☾", id="theme-toggle", cls="theme-btn pub-theme",
                       aria_label="Toggle dark mode", onclick="toggleTheme()"),
                content
            ),
            feedback_widget(lang),
            Script(SHELL_SCRIPT)
        )
    )


def alert(message: str, type: str = "error"):
    return Div(message, cls=f"alert alert-{type}") if message else ""


def fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%-d %b %Y")
    except Exception:
        return iso[:10]
    

def enum_label(_, kind: str, value) -> str:
    """Translate a stored device enum slug ("operational", "donated") with the
    labels the registration form uses (new_device.status_*, new_device.acquisition_*).
    Unknown slugs fall back to the raw value."""
    if not value:
        return _("common.fallback")
    return _(f"new_device.{kind}_{value}", str(value))


def _script_json(value) -> str:
    """json.dumps that is safe inside a <script> element (same as _js_json in
    features/faults/pages/fault_list.py): <, > and & become \\u escapes."""
    return (json.dumps(value, ensure_ascii=False)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


def map_component(lat=0, lng=0, zoom=13, markers=None, height="500px", fit=False):
    """
    markers = [
        {"lat": 0.3476, "lng": 32.5825, "title": "Mulago Hospital"},
        {"lat": 0.3200, "lng": 32.5700, "title": "Clinic B"},
    ]
    """
    markers = markers or []
    lat, lng, zoom = float(lat), float(lng), int(zoom)

    # Titles are user data (device and healthsite names): pass them as escaped
    # JSON and show them as text, since bindPopup() renders a string as HTML.
    # An apostrophe in a name used to break the script and stop the map loading.
    marker_js = "\n".join([
        f"L.marker([{float(m['lat'])}, {float(m['lng'])}]).addTo(map).bindPopup(_mapText({_script_json(m.get('title', ''))}));"
        for m in markers
    ])

    if fit and markers:
        coords = ", ".join(f"[{float(m['lat'])}, {float(m['lng'])}]" for m in markers)
        fit_js = f"map.fitBounds(L.latLngBounds([{coords}]));"
    else:
        fit_js = ""

    return Div(
        # Leaflet CSS
        Link(rel="stylesheet",
             href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"),

        # Map container
        Div(id="map", style=f"height:{height}; width:100%; border-radius:10px;"),

        # Leaflet JS + init
        Script(src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"),
        Script(f"""
            var map = L.map('map').setView([{lat}, {lng}], {zoom});
            function _mapText(t) {{ var s = document.createElement('span'); s.textContent = t; return s; }}

            L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);

            {marker_js}
            {fit_js}
        """),
        style="margin-top:12px;margin-bottom:12px;",
        cls="card"
    )

def qr_scanner_component(target_url="/devices/scan-result", lang: str = "en",
                         error: str = "", value: str = ""):
    _ = make_t(lang)
    return Div(
        Button(
            _("qr.scan"),
            id="btn-open-scanner",
            cls="btn btn-primary",
            onclick="openScanner()"
        ),
        # Scanner container, hidden until opened
        Div(
            Div(id="qr-reader", style="width:100%;max-width:400px;margin:16px auto;"),
            Button(_("qr.cancel"), id="btn-close-scanner", cls="btn btn-secondary",
                   onclick="closeScanner()"),
            id="scanner-wrapper",
            style="display:none;text-align:center;"
        ),
        # Fallback manual entry
        Div(
            Label(_("qr.manual_label"), cls="label"),
            Input(id="manual-code", cls="input", value=value,
                  placeholder=_("qr.manual_placeholder")),
            # Sits between the field and the button, matching the alert the
            # login page shows for a failed submit.
            Div(error, cls="alert alert-error",
                style="margin:10px 0 0 0;text-align:left;") if error else "",
            Button(_("qr.manual_submit"), cls="btn btn-secondary", onclick="submitManualCode()",
                   style="margin-top:10px;"),
            style="margin-top:12px;"
        ),
        Script(f"""
        let html5QrCode = null;

        function openScanner() {{
            document.getElementById('scanner-wrapper').style.display = 'block';
            document.getElementById('btn-open-scanner').style.display = 'none';

            html5QrCode = new Html5Qrcode("qr-reader");
            const config = {{ fps: 10, qrbox: {{ width: 250, height: 250 }} }};

            html5QrCode.start(
                {{ facingMode: "environment" }},  // rear camera
                config,
                (decodedText) => {{
                    // Success — stop scanner and navigate
                    html5QrCode.stop().then(() => {{
                        window.location.href = "{target_url}?code=" + encodeURIComponent(decodedText);
                    }});
                }},
                (errorMessage) => {{
                    // Ignore per-frame decode errors (fires constantly while scanning)
                }}
            ).catch((err) => {{
                alert("{_('qr.camera_error')} " + err);
                closeScanner();
            }});
        }}

        function closeScanner() {{
            if (html5QrCode) {{
                html5QrCode.stop().catch(() => {{}});
            }}
            document.getElementById('scanner-wrapper').style.display = 'none';
            document.getElementById('btn-open-scanner').style.display = 'inline-block';
        }}

        function submitManualCode() {{
            const code = document.getElementById('manual-code').value.trim();
            if (code) {{
                window.location.href = "{target_url}?code=" + encodeURIComponent(code);
            }}
        }}
        """)
    )

def assignee_options(assignees, current: str = "", lang: str = "en"):
    _ = make_t(lang)
    opts = [Option(_("maintenance_log.assignee_none"), value="",
                   selected=(not current))]
    for a in assignees:
        role_label = _("role." + (a.get("role") or "technician"))
        opts.append(Option(
            f"{a.get('full_name','')} — {role_label}",
            value=a["id"],
            selected=(str(a["id"]) == str(current)),
        ))
    return opts
