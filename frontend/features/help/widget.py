# features/help/widget.py — what the in-app help adds to the floating "?"
# button (components.feedback_widget): "How this page works" when a guide
# documents the current path (longest pattern wins, see content.py), which
# opens a small panel with that guide's steps, and "Learn the app".

from fasthtml.common import *

from components import current_user_ctx, is_authenticated, lucide
from features.help.content import docs_url, guide_for_path
from features.help.ui import HELP_CSS, steps_list
from i18n import t as make_t

HELP_JS = """
function openHelpPanel(){
  if (typeof toggleFeedbackMenu === 'function') toggleFeedbackMenu(false);
  var d = document.getElementById('help-panel');
  if (!d) return;
  if (d.showModal) { if (!d.open) d.showModal(); } else { d.setAttribute('open', ''); }
}
function closeHelpPanel(){
  var d = document.getElementById('help-panel');
  if (!d) return;
  if (d.close) d.close(); else d.removeAttribute('open');
}
(function(){
  var d = document.getElementById('help-panel');
  if (!d) return;
  // A click on the dimmed backdrop (the dialog itself, outside its card) closes it.
  d.addEventListener('click', function(e){ if (e.target === d) closeHelpPanel(); });
})();
"""


def help_panel(guide, lang: str, signed_in: bool):
    _ = make_t(lang)
    # Signed out (public QR page, library): the guide pages need a login,
    # so the panel links to the documentation site instead.
    full = (A(_("help.open_full"), lucide("arrow-right"), href=f"/community/guides/{guide.slug}",
              cls="btn btn-primary")
            if signed_in else
            A(_("help.full_guide"), lucide("external"), href=docs_url(guide),
              target="_blank", rel="noopener", cls="btn btn-primary"))
    return Dialog(
        Div(
            Div(
                Span(lucide(guide.icon), cls="hg-ico", aria_hidden="true"),
                Div(Div(_("help.this_page"), cls="help-eyebrow"),
                    H2(_(f"{guide.key}.title"), id="help-panel-title"), cls="grow"),
                Button(lucide("x"), type="button", cls="help-x", aria_label=_("help.close"),
                       onclick="closeHelpPanel()"),
                cls="help-head",
            ),
            steps_list(guide, _, go_links=signed_in),
            Div(full, cls="help-acts"),
            cls=f"help-in hp-w-{guide.world}",
        ),
        id="help-panel", cls="help-dlg", aria_labelledby="help-panel-title",
    )


def help_menu(lang: str = "en"):
    """(menu entries, extra elements) for the "?" widget."""
    _ = make_t(lang)
    user = current_user_ctx()
    signed_in = is_authenticated()
    path = user.get("path") or ""
    items, extra = [], [Style(HELP_CSS)]
    guide = None
    if path and not path.startswith("/community/guides"):
        guide = guide_for_path(path, user)
    if guide:
        items.append(Button(Span(lucide("help"), cls="nav-menu-ico"), _("help.this_page"),
                            type="button", cls="fb-help", onclick="openHelpPanel()"))
        extra += [help_panel(guide, lang, signed_in), Script(HELP_JS)]
    if signed_in:
        items.append(A(Span(lucide("learn"), cls="nav-menu-ico"), _("nav.learn"),
                       href="/community/guides", cls="fb-help"))
    if items:
        items.append(Div(cls="fb-sep", role="separator"))
    return items, extra
