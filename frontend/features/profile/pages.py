import asyncio
from fasthtml.common import *
from starlette.responses import RedirectResponse, Response
import features.profile.api as profile_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell

rt = APIRouter()

_AVATAR_IMG_STYLE = (
    "width:110px;height:110px;border-radius:50%;object-fit:cover;"
    "background:var(--c-bg-2);border:2px solid var(--c-border);"
)
_TRANSPARENT_GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="


def _avatar_section(me, _=None):
    _ = _ or (lambda k: k)
    avatar_key = me.get("avatar_key", "") or ""
    src = f"/profile/photo?v={avatar_key}" if avatar_key else _TRANSPARENT_GIF
    return Div(
        Label(_("profile.photo_label"), cls="label"),
        Img(id="avatar-preview", src=src, alt="", style=_AVATAR_IMG_STYLE),
        Label(_("profile.photo_choose"), cls="label", for_="photo-file",
              style="margin-top:8px;"),
        Input(type="file", id="photo-file", name="avatar", accept="image/*",
              onchange="previewAvatar(this)"),
        cls="form-group",
        style="margin-bottom:20px;",
    )


def _account_section(me, _=None, saved=False, error=None):
    _ = _ or (lambda k: k)
    save_msg = (Div(_("profile.saved"), cls="alert alert-success",
                    style="max-width:320px;margin-top:8px;display:block",
                    id="save-msg")
                if saved else None)
    return Div(
        H3(_("profile.basic_info"), cls="card-title"),
        Div(
            Div(
                _avatar_section(me, _),
                cls="profile-photo-side",
            ),
            Div(
                Div(
                    Label(_("profile.full_name_label"), cls="label", for_="full_name"),
                    Input(id="full_name", name="full_name", type="text",
                          value=me.get("full_name", ""), cls="input",
                          style="max-width:320px;"),
                    cls="form-group"
                ),
                Div(
                    Label(_("profile.username_label"), cls="label", for_="username"),
                    Input(id="username", name="username", type="text",
                          value=me.get("username", ""), cls="input",
                          style="max-width:320px;"),
                    cls="form-group"
                ),
                Div(
                    Label(_("profile.country_label"), cls="label", for_="country"),
                    Input(id="country", name="country", type="text",
                          value=me.get("country", "") or "", cls="input",
                          style="max-width:320px;"),
                    cls="form-group"
                ),
                save_msg,
                *([Div(e, cls="alert alert-error", style="max-width:320px;margin-top:8px;")
                   for e in ([error] if error else [])]),
                Button(_("profile.save"), type="submit", cls="btn btn-primary",
                       style="margin-top:8px;"),
                cls="profile-fields",
            ),
            cls="profile-basic",
        ),
        cls="card",
    )


def _stats_section(stats, _=None):
    _ = _ or (lambda k: k)
    stats = stats or {}
    return Div(
        H3(_("profile.stats_heading"), cls="card-title"),
        Div(
            Div(
                Div(_("profile.stats_devices"), cls="stat-label"),
                Div(str(stats.get("devices_registered", 0)), cls="stat-num"),
                cls="stat-card",
            ),
            Div(
                Div(_("profile.stats_faults_resolved"), cls="stat-label"),
                Div(str(stats.get("faults_resolved", 0)), cls="stat-num"),
                cls="stat-card g",
            ),
            Div(
                Div(_("profile.stats_maint_performed"), cls="stat-label"),
                Div(str(stats.get("maintenance_performed", 0)), cls="stat-num"),
                cls="stat-card a",
            ),
            cls="stat-grid",
        ),
        cls="card",
        style="max-width:720px;margin-top:20px;",
    )


def _content(me, _, stats=None, saved=False, error=None):
    return Div(
        Div(H1(_("profile.heading")), cls="page-header"),
        Form(
            _account_section(me, _, saved=saved, error=error),
            method="post", action="/profile",
            enctype="multipart/form-data",
            style="max-width:720px;"
        ),
        _stats_section(stats, _),
        Script("""
function previewAvatar(input) {
    if (input.files && input.files[0]) {
        var img = document.getElementById('avatar-preview');
        var reader = new FileReader();
        reader.onload = function (e) { img.src = e.target.result; };
        reader.readAsDataURL(input.files[0]);
    }
}
"""),
    )


@rt("/profile")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    me, stats = await asyncio.gather(
        profile_api.get_me(token),
        profile_api.get_profile_stats(token),
        return_exceptions=True,
    )
    if isinstance(me, Exception):
        me = {"username": "", "full_name": "", "country": "", "organizations": [], "avatar_key": ""}
    if isinstance(stats, Exception):
        stats = {}

    return page_shell(_content(me, _, stats=stats), current="/profile", title=_("title.profile"), lang=lang)


@rt("/profile")
async def post(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    form = await req.form()
    username = (form.get("username") or "").strip()
    full_name = (form.get("full_name") or "").strip()
    country = (form.get("country") or "").strip()
    avatar_file = form.get("avatar")

    error = None
    saved = False
    try:
        await profile_api.update_profile(token, {
            "username": username,
            "full_name": full_name,
            "country": country,
        })
        saved = True
    except Exception as e:
        error = str(e)

    avatar_key = ""
    if saved and avatar_file is not None and getattr(avatar_file, "filename", ""):
        try:
            content = await avatar_file.read()
            if content:
                resp = await profile_api.upload_avatar(
                    token,
                    avatar_file.filename or "avatar.jpg",
                    content,
                    getattr(avatar_file, "content_type", None),
                )
                avatar_key = resp.get("avatar_key", "")
        except Exception as e:
            error = str(e)

    me, stats = await asyncio.gather(
        profile_api.get_me(token),
        profile_api.get_profile_stats(token),
        return_exceptions=True,
    )
    if isinstance(me, Exception):
        me = {"username": username, "full_name": full_name, "country": country,
              "organizations": [], "avatar_key": avatar_key}
    if isinstance(stats, Exception):
        stats = {}

    if avatar_key:
        me["avatar_key"] = avatar_key

    if saved and "token" in req.session:
        name = me.get("full_name") or me.get("username") or req.session.get("user_email", "")
        req.session["user_name"] = name
        req.session["user_username"] = me.get("username") or name
        req.session["user_avatar"] = me.get("avatar_key") or ""

    if not saved:
        me["full_name"] = full_name
        me["username"] = username
        me["country"] = country

    return page_shell(_content(me, _, stats=stats, saved=saved, error=error),
                      current="/profile", title=_("title.profile"), lang=lang)


@rt("/profile/photo")
async def get_photo(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        content, ctype = await profile_api.get_avatar(token)
        return Response(content=content, media_type=ctype)
    except Exception:
        return Response(status_code=404)