# features/onboarding/ui.py — small shared pieces for the onboarding pages.
# Colours and radii come from the app's tokens (components.CSS); status words
# go through components.status_badge so the colour rule lives in one place.

from fasthtml.common import *

from components import status_badge

ONBOARDING_CSS = """
.ob-progress { height:8px; border-radius:9999px; background:var(--c-bg-2); overflow:hidden; margin:8px 0 4px; }
.ob-progress > span { display:block; height:100%; background:var(--c-primary); border-radius:9999px; }
.ob-quest { display:flex; gap:14px; align-items:flex-start; padding:14px 0; border-top:1px solid var(--c-border); }
.ob-quest:first-of-type { border-top:none; }
.ob-quest-body { flex:1; min-width:0; }
.ob-quest-title { font-weight:600; margin:0 0 2px; }
.ob-quest-desc { color:var(--c-text-2); font-size:.875rem; margin:0 0 8px; }
.ob-num { width:28px; height:28px; border-radius:50%; flex-shrink:0; display:flex; align-items:center; justify-content:center;
          font-size:.8rem; font-weight:600; background:var(--c-bg-2); color:var(--c-text-2); }
.ob-num.done { background:var(--c-green-lt); color:var(--c-green); }
.ob-next { border-left:3px solid var(--c-primary); }
.ob-locked { border-left:3px solid var(--c-amber); }
.ob-muted { color:var(--c-text-3); font-size:.85rem; }
.ob-actions { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.ob-tabs { display:flex; gap:4px; border-bottom:1px solid var(--c-border); margin:8px 0 16px; max-width:960px; }
.ob-tabs a { padding:8px 14px; text-decoration:none; color:var(--c-text-2); font-weight:500; font-size:.875rem;
             border-bottom:2px solid transparent; margin-bottom:-1px; }
.ob-tabs a.active { color:var(--c-primary); border-bottom-color:var(--c-primary); }
.ob-list { list-style:none; padding:0; margin:0; }
.ob-list li { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:10px 0;
              border-top:1px solid var(--c-border); flex-wrap:wrap; }
.ob-list li:first-child { border-top:none; }
.ob-steps { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:18px; }
.ob-steps span { font-size:.75rem; padding:3px 10px; border-radius:9999px; background:var(--c-bg-2); color:var(--c-text-3); }
.ob-steps span.active { background:var(--c-primary-lt); color:var(--c-primary); font-weight:600; }
.ob-steps span.done { background:var(--c-green-lt); color:var(--c-green); }
@media (max-width:640px) { .ob-quest { gap:10px; } }
"""


def progress(done: int, total: int, _):
    pct = int(100 * done / total) if total else 0
    return Div(
        Div(Span(style=f"width:{pct}%"), cls="ob-progress", role="progressbar",
            aria_valuenow=str(done), aria_valuemin="0", aria_valuemax=str(total)),
        P(_("ob.progress").format(done=done, total=total), cls="ob-muted"),
    )


def quest_row(num: int, done: bool, title: str, desc: str, *actions):
    return Div(
        Div("✓" if done else str(num), cls="ob-num done" if done else "ob-num"),
        Div(
            Div(P(title, cls="ob-quest-title"), status_badge("done" if done else "todo", "quest"),
                style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;"),
            P(desc, cls="ob-quest-desc"),
            Div(*actions, cls="ob-actions") if actions and not done else "",
            cls="ob-quest-body",
        ),
        cls="ob-quest",
    )


def clinic_tabs(org_id: str, current: str, _):
    return Nav(
        A(_("ob.tab_overview"), href=f"/groups/{org_id}", cls="active" if current == "overview" else ""),
        A(_("ob.tab_engineers"), href=f"/groups/{org_id}/engineers", cls="active" if current == "engineers" else ""),
        cls="ob-tabs",
    )


def setup_steps(current: int, _, invited: bool = True):
    labels = [_("ob.step_find"), _("ob.step_profile"),
              _("ob.step_engineers") if invited else _("ob.step_talk")]
    return Div(*[
        Span(f"{i + 1}. {label}", cls="active" if i + 1 == current else ("done" if i + 1 < current else ""))
        for i, label in enumerate(labels)
    ], cls="ob-steps")


def error_detail(e) -> str:
    try:
        return e.response.json().get("detail", "") or ""
    except Exception:
        return str(e)
