from fasthtml.common import *
from starlette.responses import RedirectResponse
import os
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper

from components import page_shell, pub_shell
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

    landing = Div(
        H1(_("home.welcome"), style="text-align:center;margin-bottom:6px;"),
        P(_("home.subtitle"), style="text-align:center;color:var(--c-text-3);margin-bottom:20px;"),
        Div(
            A(_("home.scan_cta"), href="/new_device", cls="btn btn-primary",
              style="justify-content:center;"),
            A(_("home.devices_cta"), href="/devices", cls="btn btn-secondary",
              style="justify-content:center;"),
            style="display:flex;gap:10px;justify-content:center;"
        ),
        cls="card", style="max-width:460px;margin:80px auto;padding:40px 32px;align-self:start;"
    )

    if redirect:
        return pub_shell(landing, title=_("title.home"), lang=lang)

    return page_shell(landing, current="/home", title=_("title.home"), lang=lang)