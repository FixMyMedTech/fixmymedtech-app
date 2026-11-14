from fasthtml.common import *
from starlette.responses import RedirectResponse
import os
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper

from components import page_shell, pub_shell, lucide
from i18n import t as make_t
rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# HOME — welcome page shown after login
# ══════════════════════════════════════════════════════════════


@rt("/")
async def get(req):
    return RedirectResponse("/home", status_code=302)


@rt("/home")
async def get(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    token, redirect = auth_helper.require_auth(req)

    # Platform brief: a gradient hero with the two main actions, then big
    # picture tiles to the main places (signed in only).
    def big(href, icon, tone, label):
        return A(Span(lucide(icon), cls=f"ph-ico t-{tone}" if tone else "ph-ico"), B(label),
                 href=href, cls="big-tile")
    landing = Div(
        Div(
            Div(H1(_("home.welcome")), P(_("home.subtitle"))),
            Div(
                A(lucide("qr"), _("home.scan_cta"), href="/new_device", cls="btn btn-light"),
                A(_("home.devices_cta"), href="/devices", cls="btn btn-ghost-light"),
                style="display:flex;gap:10px;flex-wrap:wrap;",
            ),
            cls="hero",
        ),
        Div(
            big("/dashboard", "dashboard", "", _("nav.dashboard")),
            big("/faults", "faults", "danger", _("nav.faults")),
            big("/community", "journey", "lead", _("nav.community")),
            big("/library", "library", "eng", _("nav.library")),
            cls="big-tiles",
        ) if not redirect else "",
        style="max-width:960px;",
    )

    if redirect and token:
        # Signed in but still a community applicant: their home is the start page.
        if req.session.pop("show_welcome", None):
            return RedirectResponse("/community/welcome", status_code=302)
        return redirect
    if redirect:
        return pub_shell(landing, title=_("title.home"), lang=lang)
    if req.session.pop("show_welcome", None):
        return RedirectResponse("/community/welcome", status_code=302)

    return page_shell(landing, current="/home", title=_("title.home"), lang=lang)