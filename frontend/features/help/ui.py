# features/help/ui.py — shared pieces of the in-app help: the CSS, the
# numbered steps, the guide card and the video card. Design-system tokens
# only; the world's colour comes from a .hp-w-<world> class (Equipment
# primary blue, Work accent teal, Community lead purple).

from fasthtml.common import *

from components import lucide
from features.help.content import Guide, href_open

HELP_CSS = """
.hp-w-equipment { --tone: var(--primary); --tone-tint: var(--primary-tint); }
.hp-w-work { --tone: var(--accent); --tone-tint: var(--accent-tint); }
.hp-w-community { --tone: var(--lead); --tone-tint: var(--lead-tint); }

/* "?" menu: help entries above feedback, a hairline between. */
.fb-menu .fb-help { all:unset; box-sizing:border-box; cursor:pointer; display:flex; align-items:center; gap:8px; padding:9px 12px; border-radius:var(--radius-control); font-size:.875rem; font-weight:600; color:var(--text); }
.fb-menu .fb-help:hover, .fb-menu .fb-help:focus-visible { background:var(--sunken); color:var(--primary); }
.fb-menu .fb-help .nav-menu-ico { color:var(--lead); }
.fb-menu .fb-sep { height:1px; background:var(--border); margin:4px 6px; }

/* Numbered steps (guide page and "?" panel). */
.hp-steps { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:var(--space-3); counter-reset:hp; }
.hp-step { display:flex; gap:var(--space-3); align-items:flex-start; }
.hp-num { flex:0 0 32px; width:32px; height:32px; border-radius:50%; display:grid; place-items:center; background:var(--tone); color:var(--surface); font-weight:800; font-size:14px; font-variant-numeric:tabular-nums; }
.hp-step-body { flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; padding-top:5px; }
.hp-step-body b { font-size:15px; color:var(--text); line-height:1.3; }
.hp-step-body p { margin:0; font-size:14px; line-height:1.5; color:var(--text-muted); }
.hp-go { display:inline-flex; align-items:center; gap:4px; margin-top:4px; font-size:13px; font-weight:700; color:var(--primary); text-decoration:none; align-self:flex-start; }
.hp-go svg { width:14px; height:14px; }
.hp-go:hover { text-decoration:underline; }

/* Guide page: big steps as cards, a side column with video and links. */
.hd { max-width:1032px; }
.hd-back { display:inline-flex; align-items:center; gap:6px; font-size:14px; font-weight:600; color:var(--text-muted); text-decoration:none; margin-bottom:var(--space-3); }
.hd-back svg { width:16px; height:16px; }
.hd-back:hover { color:var(--primary); }
.hd-chip { display:inline-flex; align-items:center; gap:6px; align-self:flex-start; padding:3px 10px 3px 4px; border-radius:var(--radius-pill); background:var(--tone-tint); color:var(--tone); font-size:12px; font-weight:700; }
.hd-chip i { width:20px; height:20px; border-radius:50%; display:grid; place-items:center; background:var(--tone); color:var(--surface); }
.hd-chip svg { width:12px; height:12px; }
.hd-split { display:flex; gap:var(--space-6); flex-wrap:wrap; align-items:flex-start; }
.hd-main { flex:999 1 520px; min-width:0; }
.hd-side { flex:1 1 280px; min-width:0; display:flex; flex-direction:column; gap:var(--space-3); }
.hd .hp-steps { gap:var(--space-3); }
.hd .hp-step { background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--tone); border-radius:var(--radius-card); box-shadow:var(--shadow-card); padding:var(--space-4); }
.hd .hp-num { flex-basis:40px; width:40px; height:40px; font-size:17px; }
.hd .hp-step-body { padding-top:2px; }
.hd .hp-step-body b { font-size:16px; }
.hd-link { display:flex; align-items:center; gap:var(--space-3); padding:var(--space-3) var(--space-4); background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-card); box-shadow:var(--shadow-card); color:var(--text); text-decoration:none; transition:transform .15s, border-color .15s; }
.hd-link:hover { transform:translateY(-2px); border-color:var(--primary); color:var(--text); }
.hd-link .hd-link-ico { width:40px; height:40px; flex-shrink:0; border-radius:var(--radius-tile); display:grid; place-items:center; background:var(--primary-tint); color:var(--primary); }
.hd-link.is-lead .hd-link-ico { background:var(--lead-tint); color:var(--lead); }
.hd-link .hd-link-ico svg { width:20px; height:20px; }
.hd-link b { display:block; font-size:14px; }
.hd-link span.sub { display:block; font-size:12px; color:var(--text-muted); line-height:1.4; }

/* Video card: a link out, nothing loads from the video site. */
.vc { display:block; border-radius:var(--radius-card); overflow:hidden; text-decoration:none; color:var(--on-brand); background:var(--frame); box-shadow:var(--shadow-card); transition:transform .15s; }
.vc:hover { transform:translateY(-2px); color:var(--on-brand); }
.vc-screen { position:relative; aspect-ratio:16/9; display:grid; place-items:center; background:radial-gradient(circle at 70% 30%, rgba(255,255,255,.10), transparent 60%), var(--frame); }
.vc-play { width:64px; height:64px; border-radius:50%; display:grid; place-items:center; background:var(--on-brand); color:var(--brand-deep); box-shadow:0 8px 24px rgba(0,0,0,.35); }
.vc-play svg { width:26px; height:26px; margin-left:4px; fill:currentColor; }
.vc-cap { padding:10px 14px 12px; display:flex; flex-direction:column; gap:2px; }
.vc-cap b { font-size:14px; color:var(--on-brand); }
.vc-cap span { font-size:12px; color:var(--on-brand); opacity:.8; display:inline-flex; align-items:center; gap:4px; }
.vc-cap svg { width:12px; height:12px; }

/* Learn the app: one section per world, cards with an icon tile. */
.hg { max-width:1032px; display:flex; flex-direction:column; gap:var(--space-6); }
.hg-wh { display:flex; align-items:center; gap:var(--space-3); margin-bottom:var(--space-3); }
.hg-wico { width:36px; height:36px; border-radius:var(--radius-tile); display:grid; place-items:center; background:var(--tone); color:var(--surface); flex-shrink:0; }
.hg-wico svg { width:20px; height:20px; }
.hg-wh h2 { font-size:20px; margin:0; color:var(--text); }
.hg-wh p { margin:0; font-size:13px; color:var(--text-muted); line-height:1.4; }
.hg-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr)); gap:var(--space-3); }
.hg-card { display:flex; flex-direction:column; gap:var(--space-3); padding:var(--space-4); background:var(--surface); border:1px solid var(--border); border-top:4px solid var(--tone); border-radius:var(--radius-card); box-shadow:var(--shadow-card); color:var(--text); text-decoration:none; transition:transform .15s, box-shadow .15s; min-width:0; }
.hg-card:hover { transform:translateY(-2px); box-shadow:var(--shadow-float); color:var(--text); }
.hg-ico { width:44px; height:44px; border-radius:12px; display:grid; place-items:center; background:var(--tone-tint); color:var(--tone); }
.hg-ico svg { width:24px; height:24px; }
.hg-card b { font-size:16px; line-height:1.3; }
.hg-card p { margin:2px 0 0; font-size:13px; line-height:1.45; color:var(--text-muted); }
.hg-meta { display:flex; gap:6px; flex-wrap:wrap; margin-top:auto; }
.hg-meta span { display:inline-flex; align-items:center; gap:4px; padding:2px 9px; border-radius:var(--radius-pill); background:var(--sunken); color:var(--text-muted); font-size:11px; font-weight:700; }
.hg-meta span.is-video { background:var(--tone-tint); color:var(--tone); }
.hg-meta svg { width:11px; height:11px; }
@media (max-width: 640px) {
  .hg { gap:var(--space-4); }
  .hg-grid { grid-template-columns:1fr; gap:var(--space-2); }
  .hg-card { display:grid; grid-template-columns:44px 1fr; grid-template-areas:"ico txt" "ico meta"; column-gap:var(--space-3); row-gap:6px; padding:var(--space-3); border-top-width:1px; border-left:4px solid var(--tone); }
  .hg-card .hg-ico { grid-area:ico; }
  .hg-card > div:not(.hg-meta) { grid-area:txt; }
  .hg-card .hg-meta { grid-area:meta; margin-top:0; }
  .hg-card b { font-size:15px; }
}

/* "How this page works" panel: a centred card on wide screens, a bottom
   sheet on phones. Native <dialog>: Escape closes it, focus stays inside. */
dialog.help-dlg { border:none; padding:0; border-radius:var(--radius-panel); background:var(--surface); color:var(--text); box-shadow:var(--shadow-float); width:min(460px, calc(100vw - 32px)); }
dialog.help-dlg::backdrop { background:rgba(19,43,69,.45); }
.help-in { display:flex; flex-direction:column; gap:var(--space-4); padding:var(--space-4) var(--space-4) var(--space-4); }
.help-head { display:flex; gap:var(--space-3); align-items:flex-start; }
.help-head .hg-ico { width:44px; height:44px; flex-shrink:0; background:var(--tone); color:var(--surface); }
.help-head .grow { flex:1; min-width:0; }
.help-eyebrow { font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--tone); }
.help-head h2 { font-size:18px; margin:2px 0 0; color:var(--text); }
.help-x { all:unset; cursor:pointer; width:34px; height:34px; border-radius:var(--radius-control); display:grid; place-items:center; color:var(--text-muted); flex-shrink:0; }
.help-x:hover, .help-x:focus-visible { background:var(--sunken); color:var(--text); }
.help-x svg { width:18px; height:18px; }
.help-acts { display:flex; gap:8px; flex-wrap:wrap; }
.help-acts .btn { flex:1 1 auto; }
@media (max-width: 640px) {
  dialog.help-dlg { width:100vw; max-width:100vw; margin:auto 0 0; border-radius:var(--radius-panel) var(--radius-panel) 0 0; max-height:85vh; }
  .help-in { padding-bottom:calc(var(--space-4) + env(safe-area-inset-bottom, 0px)); }
}
:focus-visible.hg-card, :focus-visible.hd-link, :focus-visible.vc { outline:2px solid var(--primary); outline-offset:2px; }
@media (prefers-reduced-motion: reduce) { .hg-card, .hd-link, .vc { transition:none; } .hg-card:hover, .hd-link:hover, .vc:hover { transform:none; } }
"""


def steps_list(guide: Guide, _, user: dict | None = None, go_links: bool = True):
    """The guide's steps as a numbered list, each with "Go there" when the
    step happens on a page this account can open."""
    from components import current_user_ctx
    here = (user if user is not None else current_user_ctx()).get("path") or ""
    items = []
    for i, href in enumerate(guide.steps, start=1):
        go = ""
        # No "Go there" to the page the person is already on.
        if go_links and href and href != here and href_open(href, user):
            go = A(_("help.go_there"), lucide("arrow-right"), href=href, cls="hp-go")
        items.append(Li(
            Span(str(i), cls="hp-num", aria_hidden="true"),
            Div(B(_(f"{guide.key}.s{i}t")), P(_(f"{guide.key}.s{i}")), go, cls="hp-step-body"),
            cls="hp-step",
        ))
    return Ol(*items, cls="hp-steps")


def guide_card(guide: Guide, _, has_video: bool = False):
    meta = [Span(_("help.steps_n").format(n=len(guide.steps)))]
    if has_video:
        meta.append(Span(lucide("play"), _("help.video"), cls="is-video"))
    return A(
        Span(lucide(guide.icon), cls="hg-ico", aria_hidden="true"),
        Div(B(_(f"{guide.key}.title")), P(_(f"{guide.key}.sum"))),
        Div(*meta, cls="hg-meta"),
        href=f"/community/guides/{guide.slug}",
        cls=f"hg-card hp-w-{guide.world}",
    )


def video_card(url: str, title: str, lang: str = "en"):
    """A privacy-friendly video slot: a link card with a play button. Nothing
    is loaded from YouTube (or any host) until the person taps it."""
    if not url:
        return ""
    from i18n import t as make_t
    _ = make_t(lang)
    return A(
        Div(Span(lucide("play"), cls="vc-play"), cls="vc-screen"),
        Div(B(_("help.video_title")), Span(title),
            Span(lucide("external"), _("help.video_sub")), cls="vc-cap"),
        href=url, target="_blank", rel="noopener noreferrer", cls="vc",
        aria_label=f'{_("help.video_title")}: {title}',
    )
