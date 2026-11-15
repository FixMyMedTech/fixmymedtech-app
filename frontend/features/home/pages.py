from fasthtml.common import *
from starlette.responses import RedirectResponse
import os
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper

from components import page_shell, pub_shell, lucide, user_worlds
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

    # Platform brief: a gradient hero with the two main actions, then one big
    # door per world this account has unlocked (signed in only). The sidebar
    # has no Home link: the logo opens this page.
    def door(w):
        return A(Span(lucide(w["icon"]), cls="door-ico"), B(w["label"]),
                 P(_(f"home.door_{w['key']}")),
                 Div(*[Span(lucide(icon), label) for _href, icon, label in w["links"][:4]], cls="door-links"),
                 href=w["href"], cls=f"door w-{w['key']}")
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
        Div(*[door(w) for w in user_worlds(lang)], cls="doors") if not redirect else "",
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