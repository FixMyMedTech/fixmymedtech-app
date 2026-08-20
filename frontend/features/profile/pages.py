from fasthtml.common import *
from starlette.responses import RedirectResponse
import features.profile.api as profile_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell

rt = APIRouter()


def _account_section(me, _=None, saved=False, error=None):
    _ = _ or (lambda k: k)
    save_msg = (Div(_("profile.saved"), cls="alert alert-success",
                    style="max-width:320px;margin-top:8px;display:block",
                    id="save-msg")
                if saved else None)
    return Div(
        Div(
            Label(_("profile.username_label"), cls="label", for_="username"),
            Input(id="username", name="username", type="text",
                  value=me.get("username", ""), cls="input",
                  style="max-width:320px;"),
            cls="form-group"
        ),
        Div(
            Label(_("profile.full_name_label"), cls="label", for_="full_name"),
            Input(id="full_name", name="full_name", type="text",
                  value=me.get("full_name", ""), cls="input",
                  style="max-width:320px;"),
            cls="form-group"
        ),
        save_msg,
        *([Div(e, cls="alert alert-error", style="max-width:320px;margin-top:8px;")
           for e in ([error] if error else [])]),
        Button(_("profile.save"), type="submit", cls="btn btn-primary",
               style="margin-top:8px;"),
    )


@rt("/profile")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await profile_api.get_me(token)
    except Exception:
        me = {"username": "", "full_name": "", "organizations": []}

    content = Div(
        Div(H1(_("profile.heading")), cls="page-header"),
        Form(
            _account_section(me, _),
            method="post", action="/profile",
            style="max-width:720px;"
        ),
    )
    return page_shell(content, current="/profile", title=_("title.profile"), lang=lang)


@rt("/profile")
async def post(req, username: str = "", full_name: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    error = None
    saved = False
    try:
        await profile_api.update_profile(token, {
            "username": username.strip(),
            "full_name": full_name.strip(),
        })
        saved = True
    except Exception as e:
        error = str(e)

    try:
        me = await profile_api.get_me(token)
    except Exception:
        me = {"username": username, "full_name": full_name, "organizations": []}

    if not saved:
        me["username"] = username
        me["full_name"] = full_name

    content = Div(
        Div(H1(_("profile.heading")), cls="page-header"),
        Form(
            _account_section(me, _, saved=saved, error=error),
            method="post", action="/profile",
            style="max-width:720px;"
        ),
    )
    return page_shell(content, current="/profile", title=_("title.profile"), lang=lang)
