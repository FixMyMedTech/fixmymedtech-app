# /community/welcome — shown once, when the last welcome quest makes the
# person an Ambassador and the platform opens.

from urllib.parse import quote

from fasthtml.common import *

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import hero
from i18n import t as make_t

rt = APIRouter()

SITE_URL = "https://fixmymedtech.org"


@rt("/community/welcome")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    req.session.pop("show_welcome", None)
    try:
        me = await community_api.get_me(token)
    except Exception:
        me = {}
    first = (me.get("full_name") or "").split(" ")[0]
    story = me.get("story") or {}
    where = ", ".join(x for x in (story.get("city"), story.get("country")) if x)
    share = "https://www.linkedin.com/sharing/share-offsite/?url=" + quote(SITE_URL, safe="")

    content = Div(
        hero(_("cj.welcome.title").format(name=first),
             _("cj.welcome.text").format(place=where) if where else _("cj.welcome.text_noplace"),
             _("cj.welcome.eyebrow")),
        Div(
            H2(_("cj.welcome.open_now")),
            Ul(
                Li(_("cj.welcome.open_platform")),
                Li(_("cj.welcome.open_tree")),
                Li(_("cj.welcome.open_members")),
                style="margin:0;padding-left:20px;color:var(--text);line-height:1.8;",
            ),
            cls="cj-card",
        ),
        Div(
            H3(_("cj.welcome.share_title")),
            P(_("cj.welcome.share_text")),
            A(_("cj.welcome.share_button"), href=share, target="_blank", rel="noopener",
              cls="btn btn-secondary btn-sm", style="align-self:flex-start;"),
            cls="cj-card",
        ),
        Div(
            A(_("cj.welcome.start_journey"), href="/community", cls="btn btn-primary"),
            A(_("cj.welcome.go_home"), href="/home", cls="btn btn-secondary"),
            cls="cj-row",
        ),
        cls="cj cj-narrow",
    )
    return page_shell(content, current="/community", title=_("cj.title.welcome"), lang=lang)
