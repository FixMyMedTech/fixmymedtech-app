# components.py — reusable FastHTML UI components

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


# ── Design tokens ────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --font-body:
		'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell,
		'Open Sans', 'Helvetica Neue', sans-serif;
  --font-display: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	--font-mono: ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace;

  /* Light */
  --c-bg:        #f9fafb;
  --c-bg-2:      #f1f5f9;
  --c-surface:   #ffffff;
  --c-border:    #e2e8f0;
  --c-primary:   #2563eb;
  --c-primary-lt: rgba(37,99,235,.10);
  --c-primary-mid: #1d4ed8;
  --c-text:      #0f172a;
  --c-text-2:    #475569;
  --c-text-3:    #94a3b8;
  --c-green:     #16a34a;
  --c-green-lt:  #dcfce7;
  --c-amber:     #d97706;
  --c-amber-lt:  #fef3c7;
  --c-red:       #dc2626;
  --c-red-lt:    #fee2e2;
  --c-blue:      #2563eb;
  --c-blue-lt:   #dbeafe;

  /* legacy aliases used by inline styles */
  --color-text:  var(--c-text);
  --color-bg-0:  var(--c-bg);
  --color-bg-1:  var(--c-bg);
  --color-bg-2:  var(--c-bg-2);
  --color-theme-1: var(--c-primary);
  --color-theme-2: var(--c-primary-mid);

  --sidebar-w: 248px;
  --topbar-h: 58px;
  --r-sm: 6px; --r-md: 8px; --r-lg: 12px;
}

:root[data-theme="dark"] {
  --c-bg:        #0f172a;
  --c-bg-2:      #1e293b;
  --c-surface:   #1e293b;
  --c-border:    #334155;
  --c-primary:   #60a5fa;
  --c-primary-lt: rgba(96,165,250,.14);
  --c-primary-mid: #93c5fd;
  --c-text:      #f1f5f9;
  --c-text-2:    #cbd5e1;
  --c-text-3:    #94a3b8;
  --c-green:     #4ade80;
  --c-green-lt:  #14532d;
  --c-amber:     #fbbf24;
  --c-amber-lt:  #78350f;
  --c-red:       #f87171;
  --c-red-lt:    #7f1d1d;
  --c-blue:      #60a5fa;
  --c-blue-lt:   #1e3a8a;
  --color-text:  var(--c-text);
  --color-bg-0:  var(--c-bg);
  --color-bg-1:  var(--c-bg);
  --color-bg-2:  var(--c-bg-2);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font-body); font-size: 14px; background: var(--c-bg); color: var(--c-text); -webkit-font-smoothing: antialiased; }
::selection { background: var(--c-primary-lt); }
h1,h2,h3 { font-family: var(--font-display); line-height: 1.25; font-weight: 700; letter-spacing: -.01em; }
h1 { font-size: 1.5rem; } h2 { font-size: 1.125rem; } h3 { font-size: 1rem; }
p { color: var(--c-text-2); font-size: 0.875rem; line-height: 1.65; }
a { color: var(--c-primary); text-decoration: none; }

/* ── Top navigation bar ───────────────────────────────────── */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; height: var(--topbar-h);
  display: flex; align-items: center; gap: 10px; padding: 0 14px;
  background: var(--c-surface); border-bottom: 1px solid var(--c-border);
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
.brand-sub { color: var(--c-text-3); font-weight: 500; font-size: .82rem; }
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
.sb-nav { flex: 1; padding: 14px 10px; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; overflow-x: hidden; }
.nav-link {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: var(--r-md);
  font-size: .875rem; font-weight: 500;
  color: var(--c-text-2); text-decoration: none; white-space: nowrap;
  transition: background .15s, color .15s;
}
.nav-link:hover { background: var(--c-bg-2); color: var(--c-text); }
.nav-link.active { background: var(--c-primary-lt); color: var(--c-primary); font-weight: 600; }
.nav-ico { width: 18px; flex-shrink: 0; text-align: center; font-size: 1rem; }
.sb-foot {
  padding: 12px 14px; border-top: 1px solid var(--c-border);
  font-size: .7rem; color: var(--c-text-3); font-family: var(--font-mono);
  white-space: nowrap; overflow: hidden;
}
.main {
  margin-left: var(--sidebar-w); flex: 1;
  padding: calc(var(--topbar-h) + 22px) 28px 32px;
  transition: margin-left .2s ease;
}

/* Collapsed sidebar (desktop fold) */
body.sidebar-collapsed .sidebar { width: 64px; }
body.sidebar-collapsed .main { margin-left: 64px; }
body.sidebar-collapsed .nav-link { justify-content: center; padding: 9px 0; }
body.sidebar-collapsed .nav-label { display: none; }
body.sidebar-collapsed .sb-foot { display: none; }

/* Buttons */
.btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; padding:8px 16px; border-radius:var(--r-md); font-family:var(--font-body); font-size:.875rem; font-weight:500; line-height:1.4; cursor:pointer; transition:all .15s; border:1px solid transparent; text-decoration:none; }
.btn-primary { background:var(--c-primary); color:#fff; }
.btn-primary:hover { background:var(--c-primary-mid); }
.btn-secondary { background:var(--c-surface); color:var(--c-text); border-color:var(--c-border); }
.btn-secondary:hover { border-color:var(--c-primary); color:var(--c-primary); }
.btn-danger { background:var(--c-red-lt); color:var(--c-red); border:1px solid transparent; }
.btn-sm { padding:4px 10px; font-size:.8rem; }
.btn-outline { background:var(--c-surface); color:var(--c-text-2); border:1px solid var(--c-border); }
.btn-outline:hover { background:var(--c-bg-2); border-color:var(--c-primary); color:var(--c-primary); }
.oauth-divider { text-align:center; font-size:.78rem; color:var(--c-text-3); margin:6px 0 10px; position:relative; }
.oauth-divider::before, .oauth-divider::after { content:""; position:absolute; top:50%; width:34%; height:1px; background:var(--c-border); }
.oauth-divider::before { left:0; }
.oauth-divider::after { right:0; }
.oauth-buttons { display:flex; flex-direction:column; gap:8px; }

/* Cards */
.card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--r-lg); padding:20px 22px; box-shadow:0 1px 2px rgba(15,23,42,.03); }
.card-title { font-size:1rem; font-weight:600; margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid var(--c-border); }
.profile-basic { display:flex; gap:24px; align-items:flex-start; }
.profile-photo-side { flex-shrink:0; display:flex; flex-direction:column; align-items:flex-start; }
.profile-photo-side input[type="file"] { max-width:170px; font-size:.78rem; }
.profile-fields { flex:1 1 auto; min-width:0; }

/* Badges */
.badge { display:inline-flex; align-items:center; padding:3px 10px; border-radius:9999px; font-size:.7rem; font-weight:600; letter-spacing:.02em; font-family:var(--font-mono); }
.badge-green { background:var(--c-green-lt); color:var(--c-green); }
.badge-amber { background:var(--c-amber-lt); color:var(--c-amber); }
.badge-red   { background:var(--c-red-lt);   color:var(--c-red);   }
.badge-blue  { background:var(--c-blue-lt);  color:var(--c-blue);  }
.badge-gray  { background:var(--c-bg-2);     color:var(--c-text-3);}

/* Forms */
.input { width:100%; padding:9px 13px; border:1px solid var(--c-border); border-radius:var(--r-md); font-family:var(--font-body); font-size:.875rem; background:var(--c-surface); color:var(--c-text); transition:border-color .15s, box-shadow .15s; }
.input:focus { outline:none; border-color:var(--c-primary); box-shadow:0 0 0 3px var(--c-primary-lt); }
.label { display:block; font-size:.8rem; font-weight:500; color:var(--c-text-2); margin-bottom:5px; }
.form-group { margin-bottom:14px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }

/* Tables */
.table-wrap { overflow-x:auto; border:1px solid var(--c-border); border-radius:var(--r-lg); }
table { width:100%; border-collapse:collapse; font-size:.875rem; }
th { text-align:left; padding:10px 14px; font-size:.7rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; font-family:var(--font-mono); color:var(--c-text-3); background:var(--c-bg-2); border-bottom:1px solid var(--c-border); }
td { padding:11px 14px; border-bottom:1px solid var(--c-border); color:var(--c-text-2); }
tr:last-child td { border-bottom:none; }
tr:hover td { background:var(--c-bg-2); }

/* Alerts */
.alert { padding:11px 14px; border-radius:var(--r-md); font-size:.875rem; margin-bottom:14px; }
.alert-error   { background:var(--c-red-lt);   color:var(--c-red);   border:1px solid transparent; }
.alert-success { background:var(--c-green-lt); color:var(--c-green); border:1px solid transparent; }
.alert-warning { background:var(--c-amber-lt); color:var(--c-amber); border:1px solid transparent; }

/* Stats grid */
.stat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:20px; }
.stat-card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--r-lg); padding:16px 18px; }
.stat-label { font-size:.7rem; font-weight:600; color:var(--c-text-3); text-transform:uppercase; letter-spacing:.06em; font-family:var(--font-mono); margin-bottom:5px; }
.stat-num { font-family:var(--font-display); font-size:2rem; font-weight:700; color:var(--c-text); line-height:1; }
.stat-sub { font-size:.72rem; color:var(--c-text-3); margin-top:3px; }
.stat-card.g { border-top:3px solid var(--c-green); }
.stat-card.a { border-top:3px solid var(--c-amber); }
.stat-card.r { border-top:3px solid var(--c-red); }

/* Two col */
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:22px; }

/* Toolbar */
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
.pill { padding:4px 12px; border-radius:9999px; font-size:.8rem; font-weight:500; background:var(--c-surface); border:1px solid var(--c-border); color:var(--c-text-2); cursor:pointer; text-decoration:none; }
.pill.active { background:var(--c-primary); color:#fff; border-color:var(--c-primary); }

/* Public QR page */
.pub-page { max-width:520px; margin:0 auto; min-height:100vh; display:flex; flex-direction:column; background:var(--c-surface); border-left:1px solid var(--c-border); border-right:1px solid var(--c-border); }
.pub-header {
  background: linear-gradient(135deg, #0f2a5c 0%, #14438b 55%, #0b6ce0 100%);
  padding:12px 16px; display:flex; align-items:center; justify-content:space-between;
}
.pub-logo { display:flex; align-items:center; gap:7px; color:#fff; font-family:var(--font-display); font-weight:700; font-size:1rem; }
.pub-cross { color:#5eead4; }
.device-identity { display:flex; align-items:flex-start; gap:12px; padding:16px; background:var(--c-surface); border-bottom:1px solid var(--c-border); }
.dev-icon { font-size:2rem; flex-shrink:0; }
.dev-cat { font-size:.7rem; color:var(--c-text-3); text-transform:uppercase; letter-spacing:.06em; font-family:var(--font-mono); }
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
  background: linear-gradient(135deg, #0f2a5c 0%, #14438b 55%, #0b6ce0 100%);
  display:flex; align-items:flex-end; padding:48px; position:relative; overflow:hidden;
}
.auth-bg::before { content:''; position:absolute; inset:0; background:radial-gradient(circle at 20% 30%, rgba(94,234,212,0.12) 0%, transparent 50%); }
.auth-quote { position:relative; font-family:var(--font-display); font-size:1.5rem; color:rgba(255,255,255,0.9); line-height:1.5; border-left:3px solid #5eead4; padding-left:20px; font-weight:600; }
.auth-quote em { color:#5eead4; }
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

/* Language select */
.input-lang {
  padding:5px 9px; border:1px solid var(--c-border);
  border-radius:var(--r-md); font-size:.75rem; font-family:var(--font-mono);
  background:var(--c-surface); color:var(--c-text);
  cursor:pointer; outline:none;
}
.input-lang:focus { border-color:var(--c-primary); }

/* Public pages (no sidebar): content starts below the fixed top bar */
.public-shell .pub-page { padding-top: var(--topbar-h); }

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
  .auth-wrap { grid-template-columns:1fr; }
  .auth-bg { display:none; }
  .auth-card { padding:32px 20px; border-right:none; }
  .form-row { grid-template-columns:1fr; }
  .profile-basic { flex-direction:column; gap:8px; }
}
"""


def status_badge(status: str, type: str = "device", lang: str = "en"):
    _ = make_t(lang)
    m = {
        "device": {
            "operational":    (_("badge.operational"),     "badge-green"),
            "maintenance":    (_("badge.maintenance"),     "badge-amber"),
            "fault":          (_("badge.fault"),           "badge-red"),
            "decommissioned": (_("badge.decommissioned"),  "badge-gray"),
        },
        "fault": {
            "open":        (_("badge.open"),        "badge-red"),
            "assigned":    (_("badge.assigned"),    "badge-amber"),
            "in_progress": (_("badge.in_progress"), "badge-blue"),
            "resolved":    (_("badge.resolved"),    "badge-green"),
        },
        "severity": {
            "low":      (_("badge.low"),      "badge-gray"),
            "medium":   (_("badge.medium"),   "badge-amber"),
            "high":     (_("badge.high"),     "badge-red"),
            "critical": (_("badge.critical"), "badge-red"),
        },
        "log": {
            "open":        (_("badge.open"),        "badge-red"),
            "in_progress": (_("badge.in_progress"), "badge-blue"),
            "closed":      (_("badge.closed"),      "badge-green"),
        },
    }
    label, cls = m.get(type, m["device"]).get(status, (status, "badge-gray"))
    return Span(label, cls=f"badge {cls}")


def sidebar(current: str = "", lang: str = "en"):
    _ = make_t(lang)
    links = [
        ("/home",     "⌂", _("nav.home")),
        ("/dashboard", "◈", _("nav.dashboard")),
        ("/devices",   "⊞", _("nav.devices")),
        ("/tasks",     "☐", _("nav.tasks")),
        ("/groups",    "⊞", _("nav.groups")),
        ("/profile",   "◉", _("nav.profile")),
        ("/logout",   "➜]", _("nav.logout")),
    ]
    return Aside(
        Div(
            A(
                Span("✚", cls="brand-mark"),
                Span("FixMyMedTech", cls="brand"),
                href="/home",
                title="FixMyMedTech",
            ),
            Button("✕", id="sb-close", cls="sb-close", aria_label="Close menu",
                   onclick="toggleSidebar(false)"),
            cls="sb-head"
        ),
        Nav(
            *[A(Span(icon, cls="nav-ico"), Span(label, cls="nav-label"), href=href,
                title=label,
                cls=f"nav-link {'active' if current == href else ''}")
              for href, icon, label in links],
            cls="sb-nav"
        ),
        cls="sidebar",
        id="app-sidebar"
    )


def language_switcher(current_lang: str):
    options = []
    for code, name in LANGUAGES.items():
        options.append(Option(name, value=code, selected=(code == current_lang)))
    return Form(
        Select(*options, name="lang", cls="input-lang",
               onchange="this.form.submit()"),
        method="post", action="/lang",
        style="display:flex;align-items:center;gap:6px;"
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
            A("◉ " + _("nav.profile"), href="/profile"),
            A("➜] " + _("nav.logout"), href="/logout"),
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
document.addEventListener('click', function(e){
  var wrap = document.getElementById('avatar-wrap');
  var menu = document.getElementById('avatar-menu');
  if (wrap && menu && menu.classList.contains('open') && !wrap.contains(e.target)) {
    menu.classList.remove('open');
  }
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
    right = [language_switcher(lang), theme_toggle()]
    if authenticated:
        right.append(avatar_menu(lang))
    else:
        right.insert(0, A(_("login.signin"), href="/login",
                          cls="btn btn-secondary btn-sm"))
    return Header(
        *left,
        A(
            Span("✚", cls="brand-mark"),
            Span("FixMyMedTech", cls="brand"),
            Span("Operations Console", cls="brand-sub"),
            href="/home" if authenticated else "/",
            title="FixMyMedTech",
            cls="brand"
        ),
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
        )
    else:
        body_inner = Div(content, cls="shell public-shell")

    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),
            Style(CSS),
        ),
        Body(
            Div(
                topbar(authenticated, current, lang),
                body_inner,
            ),
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
            Style(CSS),
        ),
        Body(
            Div(
                Div(language_switcher(lang), cls="lang-fab"),
                Button("☾", id="theme-toggle", cls="theme-btn pub-theme",
                       aria_label="Toggle dark mode", onclick="toggleTheme()"),
                content
            ),
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
    

def map_component(lat=0, lng=0, zoom=13, markers=None, height="500px", fit=False):
    """
    markers = [
        {"lat": 0.3476, "lng": 32.5825, "title": "Mulago Hospital"},
        {"lat": 0.3200, "lng": 32.5700, "title": "Clinic B"},
    ]
    """
    markers = markers or []

    # Build JS marker code
    marker_js = "\n".join([
        f"L.marker([{m['lat']}, {m['lng']}]).addTo(map).bindPopup('{m.get('title', '')}');"
        for m in markers
    ])

    if fit and markers:
        coords = ", ".join(f"[{m['lat']}, {m['lng']}]" for m in markers)
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

            L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);

            {marker_js}
            {fit_js}
        """),
        style="margin-top:12px;margin-bottom:12px;",
        cls="card"
    )

def qr_scanner_component(target_url="/devices/scan-result", lang: str = "en"):
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
            Input(id="manual-code", cls="input", placeholder=_("qr.manual_placeholder")),
            Button(_("qr.manual_submit"), cls="btn btn-secondary", onclick="submitManualCode()"),
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