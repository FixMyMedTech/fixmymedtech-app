# features/help/pages.py — "Learn the app".
#
#   /community/guides          the guides this account can use, by world
#   /community/guides/{slug}   one guide: numbered steps, "Go there" links,
#                              a video card (HELP_VIDEO_<SLUG>), the full
#                              guide on the docs site (DOCS_URL) and
#                              "Suggest an improvement" (the feedback form)
#
# Content is data in content.py; texts are help.* keys in i18n.py.

from urllib.parse import urlencode

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
from components import WORLD_ICONS, current_user_ctx, lucide, page_head, page_shell
from features.help.content import BY_SLUG, docs_url, grouped_for, video_url, visible
from features.help.ui import guide_card, steps_list, video_card
from i18n import t as make_t

rt = APIRouter()

HOME = "/community/guides"


@rt(HOME, methods=["get"])
async def guides_index(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    sections = []
    for world, guides in grouped_for():
        sections.append(Section(
            Div(Span(lucide(WORLD_ICONS[world]), cls="hg-wico", aria_hidden="true"),
                Div(H2(_(f"nav.world_{world}")), P(_(f"home.door_{world}"))),
                cls="hg-wh"),
            Div(*[guide_card(g, _, bool(video_url(g))) for g in guides], cls="hg-grid"),
            cls=f"hp-w-{world}",
        ))
    if not sections:
        sections = [Div(Div(lucide("learn"), cls="empty-ico"), B(_("help.empty")), cls="empty")]
    content = Div(
        page_head(_("help.page_title"), _("help.page_sub"), "learn", "lead"),
        *sections,
        cls="hg",
    )
    return page_shell(content, current=HOME, title=_("help.title"), lang=lang)


@rt(HOME + "/{slug}", methods=["get"])
async def guide_page(req, slug: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    guide = BY_SLUG.get(slug)
    if guide is None or not visible(guide):
        return RedirectResponse(HOME, status_code=302)
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    title = _(f"{guide.key}.title")
    feedback = "/feedback?" + urlencode({
        "type": "feedback",
        "page": f"{HOME}/{slug}",
        "summary": _("help.suggest_summary").format(title=title),
    })
    side = Div(
        video_card(video_url(guide), title, lang),
        A(Span(lucide("external"), cls="hd-link-ico"),
          Div(B(_("help.full_guide")), Span(_("help.full_guide_sub"), cls="sub")),
          href=docs_url(guide), target="_blank", rel="noopener", cls="hd-link"),
        A(Span(lucide("message"), cls="hd-link-ico"),
          Div(B(_("help.suggest")), Span(_("help.suggest_sub"), cls="sub")),
          href=feedback, cls="hd-link is-lead"),
        cls="hd-side",
    )
    chip = Span(I(lucide(WORLD_ICONS[guide.world])), _(f"nav.world_{guide.world}"),
                cls="hd-chip")
    content = Div(
        A(lucide("arrow-left"), _("help.back"), href=HOME, cls="hd-back"),
        page_head(title, Div(P(_(f"{guide.key}.sum")), chip,
                             style="display:flex;flex-direction:column;gap:8px;"),
                  guide.icon, "lead"),
        Div(Div(steps_list(guide, _, current_user_ctx()), cls="hd-main"), side, cls="hd-split"),
        cls=f"hd hp-w-{guide.world}",
    )
    return page_shell(content, current=HOME, title=f"{title} — FixMyMedTech", lang=lang)
