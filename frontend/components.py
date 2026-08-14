# components.py — reusable FastHTML UI components

from fasthtml.common import *
from i18n import LANGUAGES, t as make_t


# ── Design tokens ────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

:root {
  --font-body:
		Arial, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell,
		'Open Sans', 'Helvetica Neue', sans-serif;
	--font-mono: 'Fira Mono', monospace;
	--color-bg-0: rgb(202, 216, 228);
	--color-bg-1: hsl(204, 33%, 94%);
	--color-bg-2: hsl(224, 44%, 95%);
	--color-theme-1: #01a2b5;
	--color-theme-2: #104f84;
	--color-text: rgba(0, 0, 0, 0.7);
	--column-width: 42rem;
	--column-margin-top: 4rem;
	font-family: var(--font-body);
	color: var(--color-text);
  --c-bg:        #f4f3ee;
  --c-bg-2:      #eceae2;
  --c-surface:   #ffffff;
  --c-border:    #d6d3c9;
  --c-primary: #104f84;
  --c-primary-lt: #d4ece5;
  --c-primary-mid: #01a2b5;
  --c-text:      #1a1916;
  --c-text-2:    #4a4740;
  --c-text-3:    #8a8780;
  --c-green:     #16a34a;
  --c-green-lt:  #dcfce7;
  --c-amber:     #d97706;
  --c-amber-lt:  #fef3c7;
  --c-red:       #dc2626;
  --c-red-lt:    #fee2e2;
  --c-blue:      #2563eb;
  --c-blue-lt:   #dbeafe;
  --font-display:'DM Serif Display', Georgia, serif;
  --font-body:   'DM Sans', system-ui, sans-serif;
  --r-md: 10px; --r-lg: 16px;
}
:root {
  --sidebar-width: 240px;
}

/* Base: escritorio */
.layout {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
}

/* Tablet/móvil: sidebar colapsa */
@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: fixed;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  .sidebar.open {
    transform: translateX(0);
  }
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font-body); background: var(--c-bg); color: var(--c-text); -webkit-font-smoothing: antialiased; }
h1,h2,h3 { font-family: var(--font-display); line-height: 1.2; }
h1 { font-size: 1.8rem; } h2 { font-size: 1.3rem; } h3 { font-size: 1.05rem; }
p { color: var(--c-text-2); font-size: 0.9rem; line-height: 1.7; }
a { color: var(--c-primary); text-decoration: none; }

/* App shell */
.shell { display: flex; min-height: 100vh; }
.sidebar { width: 210px; flex-shrink: 0; background: var(--c-primary); display: flex; flex-direction: column; position: fixed; top:0; left:0; bottom:0; z-index:100; }
.sb-head { display:flex; align-items:center; border-bottom:1px solid rgba(255,255,255,0.1); }
.sb-logo { display:flex; align-items:center; gap:8px; padding:20px 16px; }
.sb-cross { color:#5eead4; font-size:1.2rem; }
.sb-name { font-family:var(--font-display); font-size:1.2rem; color:#fff; }
.sb-nav { flex:1; padding:14px 10px; display:flex; flex-direction:column; gap:3px; }
.nav-link { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:var(--r-md); font-size:0.875rem; font-weight:500; color:rgba(255,255,255,0.6); text-decoration:none; transition:all .15s; }
.nav-link:hover,.nav-link.active { background:rgba(255,255,255,0.15); color:#fff; }
.sb-foot { padding:12px 10px; border-top:1px solid rgba(255,255,255,0.1); font-size:0.75rem; color:rgba(255,255,255,0.5); }
.main { margin-left:210px; flex:1; padding:28px 32px; }
.lang-fab { position:fixed; bottom:16px; left:16px; z-index:200; }

/* Buttons */
.btn { display:inline-flex; align-items:center; gap:6px; padding:9px 18px; border-radius:var(--r-md); font-family:var(--font-body); font-size:0.875rem; font-weight:500; cursor:pointer; transition:all .15s; border:none; text-decoration:none; }
.btn-primary { background:var(--c-primary); color:#fff; }
.btn-primary:hover { background:var(--c-primary-md); }
.btn-secondary { background:var(--c-bg-2); color:var(--c-text); border:1px solid var(--c-border); }
.btn-danger { background:var(--c-red-lt); color:var(--c-red); border:1px solid #fca5a5; }
.btn-sm { padding:5px 12px; font-size:0.8rem; }

/* Cards */
.card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--r-lg); padding:18px 20px; }

/* Badges */
.badge { display:inline-flex; align-items:center; padding:2px 9px; border-radius:20px; font-size:0.75rem; font-weight:500; }
.badge-green { background:var(--c-green-lt); color:var(--c-green); }
.badge-amber { background:var(--c-amber-lt); color:var(--c-amber); }
.badge-red   { background:var(--c-red-lt);   color:var(--c-red);   }
.badge-blue  { background:var(--c-blue-lt);  color:var(--c-blue);  }
.badge-gray  { background:var(--c-bg-2);     color:var(--c-text-3);}

/* Forms */
.input { width:100%; padding:9px 13px; border:1px solid var(--c-border); border-radius:var(--r-md); font-family:var(--font-body); font-size:0.875rem; background:var(--c-surface); color:var(--c-text); }
.input:focus { outline:none; border-color:var(--c-primary); box-shadow:0 0 0 3px var(--c-primary-lt); }
.label { display:block; font-size:0.8rem; font-weight:500; color:var(--c-text-2); margin-bottom:5px; }
.form-group { margin-bottom:14px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }

/* Tables */
.table-wrap { overflow-x:auto; border:1px solid var(--c-border); border-radius:var(--r-lg); }
table { width:100%; border-collapse:collapse; font-size:0.875rem; }
th { text-align:left; padding:10px 14px; font-size:0.75rem; font-weight:600; letter-spacing:.05em; text-transform:uppercase; color:var(--c-text-3); background:var(--c-bg); border-bottom:1px solid var(--c-border); }
td { padding:11px 14px; border-bottom:1px solid var(--c-border); color:var(--c-text-2); }
tr:last-child td { border-bottom:none; }
tr:hover td { background:var(--c-bg); }

/* Alerts */
.alert { padding:11px 14px; border-radius:var(--r-md); font-size:0.875rem; margin-bottom:14px; }
.alert-error   { background:var(--c-red-lt);   color:var(--c-red);   border:1px solid #fca5a5; }
.alert-success { background:var(--c-green-lt); color:var(--c-green); border:1px solid #86efac; }
.alert-warning { background:var(--c-amber-lt); color:var(--c-amber); border:1px solid #fcd34d; }

/* Stats grid */
.stat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:20px; }
.stat-card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--r-lg); padding:16px 18px; }
.stat-label { font-size:0.72rem; font-weight:500; color:var(--c-text-3); text-transform:uppercase; letter-spacing:.04em; margin-bottom:5px; }
.stat-num { font-family:var(--font-display); font-size:2rem; color:var(--c-text); line-height:1; }
.stat-sub { font-size:0.72rem; color:var(--c-text-3); margin-top:3px; }
.stat-card.g { border-top:3px solid var(--c-green); }
.stat-card.a { border-top:3px solid var(--c-amber); }
.stat-card.r { border-top:3px solid var(--c-red); }

/* Two col */
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:22px; }

/* Toolbar */
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
.pill { padding:4px 12px; border-radius:20px; font-size:0.8rem; font-weight:500; background:var(--c-surface); border:1px solid var(--c-border); color:var(--c-text-2); cursor:pointer; text-decoration:none; }
.pill.active { background:var(--c-primary); color:#fff; border-color:var(--c-primary); }

/* Public QR page */
.pub-page { max-width:520px; margin:0 auto; min-height:100vh; display:flex; flex-direction:column; background:var(--c-bg); }
.pub-header { background:var(--c-primary); padding:12px 16px; display:flex; align-items:center; justify-content:space-between; }
.pub-logo { display:flex; align-items:center; gap:7px; color:#fff; font-family:var(--font-display); font-size:1rem; }
.pub-cross { color:#5eead4; }
.device-identity { display:flex; align-items:flex-start; gap:12px; padding:16px; background:var(--c-surface); border-bottom:1px solid var(--c-border); }
.dev-icon { font-size:2rem; flex-shrink:0; }
.dev-cat { font-size:0.72rem; color:var(--c-text-3); text-transform:uppercase; letter-spacing:.04em; }
.dev-name { font-size:1.2rem; font-family:var(--font-display); margin:2px 0; }
.dev-meta { font-size:0.78rem; color:var(--c-text-3); }
.dev-status { flex-shrink:0; text-align:right; }
.dev-loc { font-size:0.72rem; color:var(--c-text-3); margin-top:4px; }
.warn-bar { display:flex; gap:8px; align-items:flex-start; background:var(--c-amber-lt); border-left:4px solid var(--c-amber); padding:11px 14px; font-size:0.85rem; color:var(--c-amber); }
.warn-bar p { color:#92400e; font-size:0.78rem; margin:2px 0 0; }
.report-cta { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:var(--c-surface); border-bottom:1px solid var(--c-border); }
.pub-tabs { display:flex; background:var(--c-surface); border-bottom:1px solid var(--c-border); margin-top:6px; }
.pub-tab { flex:1; padding:10px 6px; font-size:0.85rem; font-weight:500; color:var(--c-text-3); background:none; border:none; cursor:pointer; border-bottom:2px solid transparent; text-align:center; text-decoration:none; }
.pub-tab.active { color:var(--c-primary); border-bottom-color:var(--c-primary); }
.info-list { display:flex; flex-direction:column; padding:8px 16px; }
.info-row { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--c-border); font-size:0.875rem; }
.info-row:last-child { border-bottom:none; }
.info-row dt { color:var(--c-text-3); font-weight:500; }
.info-row dd { color:var(--c-text); font-weight:500; }
.pub-section { padding:14px 16px; }
.pub-footer { margin-top:auto; padding:16px; text-align:center; border-top:1px solid var(--c-border); font-size:0.75rem; color:var(--c-text-3); }

/* Login / Signup */
.auth-wrap { min-height:100vh; display:grid; grid-template-columns:440px 1fr; }
.auth-card { padding:48px 40px; display:flex; flex-direction:column; justify-content:center; background:var(--c-surface); border-right:1px solid var(--c-border); }
.auth-brand { margin-bottom:28px; }
.brand-icon { font-size:1.8rem; color:var(--c-primary); display:block; margin-bottom:8px; }
.auth-bg { background:var(--c-primary); display:flex; align-items:flex-end; padding:48px; position:relative; overflow:hidden; }
.auth-bg::before { content:''; position:absolute; inset:0; background:radial-gradient(circle at 20% 30%, rgba(94,234,212,0.12) 0%, transparent 50%); }
.auth-quote { position:relative; font-family:var(--font-display); font-size:1.5rem; color:rgba(255,255,255,0.9); line-height:1.5; border-left:3px solid #5eead4; padding-left:20px; }
.auth-quote em { color:#5eead4; }
.auth-link { margin-top:14px; font-size:0.82rem; color:var(--c-text-3); text-align:center; }
.auth-link a { color:var(--c-primary); font-weight:500; }

/* Overdue */
.overdue { color:var(--c-red); font-weight:500; }
.overdue-tag { display:inline-block; margin-left:3px; background:var(--c-red-lt); color:var(--c-red); font-size:0.7rem; padding:1px 5px; border-radius:10px; }

/* Mobile: hamburger toggle */
.sb-toggle, .sb-backdrop, .sb-close { display:none; }

@media (max-width:768px) {
  .shell { flex-direction:column; }
  .sidebar {
    position:fixed; top:0; left:0; bottom:0;
    width:260px; height:100vh;
    transform:translateX(-100%);
    transition:transform .22s ease;
    box-shadow:2px 0 18px rgba(0,0,0,.25);
    z-index:250;
  }
  .sidebar.open { transform:translateX(0); }
  .main { margin-left:0; padding:16px; padding-top:68px; }
  .sb-toggle {
    display:flex; align-items:center; justify-content:center;
    position:fixed; top:12px; left:12px; z-index:300;
    width:44px; height:44px; border:none; border-radius:var(--r-md);
    background:var(--c-primary); color:#fff; font-size:1.35rem; cursor:pointer;
    box-shadow:0 2px 10px rgba(0,0,0,.18);
  }
  .sb-close {
    display:flex; align-items:center; justify-content:center;
    margin-left:auto; margin-right:12px;
    width:36px; height:36px; flex-shrink:0;
    border:none; border-radius:var(--r-md);
    background:rgba(255,255,255,0.15); color:#fff; font-size:1.05rem; cursor:pointer;
  }
  .sb-close:active { background:rgba(255,255,255,0.3); }
  .sb-backdrop {
    display:block; position:fixed; inset:0; z-index:240;
    background:rgba(0,0,0,.45); opacity:0; pointer-events:none;
    transition:opacity .22s ease;
  }
  .sb-backdrop.show { opacity:1; pointer-events:auto; }
  .stat-grid { grid-template-columns:1fr 1fr; }
  .two-col { grid-template-columns:1fr; }
  .auth-wrap { grid-template-columns:1fr; }
  .auth-bg { display:none; }
  .auth-card { padding:32px 20px; }
  .form-row { grid-template-columns:1fr; }
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
        ("/dashboard", "◈", _("nav.dashboard")),
        ("/devices",   "⊞", _("nav.devices")),
        ("/logout",   "➜]", _("nav.logout")),
    ]
    return Aside(
        Div(
            Div(Span("✚", cls="sb-cross"), Span("FixMyMedTech", cls="sb-name"), cls="sb-logo"),
            Button("✕", id="sb-close", cls="sb-close", aria_label="Close menu",
                   onclick="toggleSidebar(false)"),
            cls="sb-head"
        ),
        Nav(
            *[A(Span(icon), f" {label}", href=href,
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
        style="display:flex;align-items:center;gap:6px;margin-left:auto;"
    )


def page_shell(content, current: str = "", title: str = "FixMyMedTech",
               lang: str = "en"):
    _ = make_t(lang)
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),
            Style(CSS),
            Style("""
                .input-lang {
                    padding:4px 8px;border:1px solid var(--c-border);
                    border-radius:var(--r-md);font-size:0.75rem;
                    background:var(--c-surface);color:var(--c-text);
                    cursor:pointer;outline:none;
                }
                .input-lang:focus { border-color:var(--c-primary); }
            """)
        ),
        Body(
            Div(
                Div(language_switcher(lang), cls="lang-fab"),
                Button("☰", id="sb-toggle", cls="sb-toggle", aria_label="Menu",
                       onclick="toggleSidebar()"),
                Div(id="sb-backdrop", cls="sb-backdrop", onclick="toggleSidebar(false)"),
                Div(
                    sidebar(current, lang),
                    Main(
                        content,
                        cls="main",
                    ),
                    cls="shell"
                ),
            ),
            Script("""
function toggleSidebar(open){
  var sb = document.getElementById('app-sidebar');
  var bd = document.getElementById('sb-backdrop');
  var tg = document.getElementById('sb-toggle');
  if(!sb) return;
  var isOpen = (typeof open === 'boolean') ? open : !sb.classList.contains('open');
  sb.classList.toggle('open', isOpen);
  if(bd) bd.classList.toggle('show', isOpen);
  if(tg) tg.style.display = isOpen ? 'none' : 'flex';
}
""")
        )
    )


def pub_shell(content, title: str = "FixMyMedTech", lang: str = "en"):
    """Shell for public QR pages — no sidebar."""

    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),
            Style(CSS),
            Style("""
                .input-lang {
                    padding:4px 8px;border:1px solid var(--c-border);
                    border-radius:var(--r-md);font-size:0.75rem;
                    background:var(--c-surface);color:var(--c-text);
                    cursor:pointer;outline:none;
                }
                .input-lang:focus { border-color:var(--c-primary); }
            """)
        ),
        Body(
            Div(language_switcher(lang), cls="lang-fab"),
            content
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

def qr_scanner_component(target_url="/devices/scan-result"):
    return Div(
        Button(
            "📷 Scan QR code",
            id="btn-open-scanner",
            cls="btn btn-primary",
            onclick="openScanner()"
        ),
        # Scanner container, hidden until opened
        Div(
            Div(id="qr-reader", style="width:100%;max-width:400px;margin:16px auto;"),
            Button("Cancel", id="btn-close-scanner", cls="btn btn-secondary",
                   onclick="closeScanner()"),
            id="scanner-wrapper",
            style="display:none;text-align:center;"
        ),
        # Fallback manual entry
        Div(
            Label("Or enter code manually:", cls="label"),
            Input(id="manual-code", cls="input", placeholder="e.g. MT-00123"),
            Button("Submit", cls="btn btn-secondary", onclick="submitManualCode()"),
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
                alert("Could not access camera: " + err);
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