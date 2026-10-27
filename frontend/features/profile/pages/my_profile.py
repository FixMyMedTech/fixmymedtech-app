# pages/my_profile.py — the signed-in user's own profile.
#
# Editable: avatar upload, name/username/country, stats. POSTs to itself.
# Also: email verification (re-send the link) and connecting a Discord account.
# A different page entirely from profile_detail (read-only, someone else's) —
# profile_detail redirects here rather than rendering for yourself.

import asyncio
import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse, Response
import features.profile.api as profile_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import (page_shell, AVATAR_IMG_STYLE, TRANSPARENT_GIF,
                        stats_section)

rt = APIRouter()


def _avatar_section(me, _=None):
    _ = _ or (lambda k: k)
    avatar_key = me.get("avatar_key", "") or ""
    src = f"/profile/photo?v={avatar_key}" if avatar_key else TRANSPARENT_GIF
    return Div(
        Label(_("profile.photo_label"), cls="label"),
        Img(id="avatar-preview", src=src, alt="", style=AVATAR_IMG_STYLE),
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


# ?verify=… / ?discord=… / ?verified=… results shown above the cards: (key, alert type)
NOTICES = {
    ("verify", "sent"):      ("profile.verify_sent", "success"),
    ("verify", "wait"):      ("profile.verify_wait", "warning"),
    ("verify", "error"):     ("profile.verify_error", "error"),
    ("verified", "1"):       ("profile.verified_ok", "success"),
    ("verified", "0"):       ("profile.verified_fail", "error"),
    ("discord", "linked"):   ("profile.discord_linked_ok", "success"),
    ("discord", "unlinked"): ("profile.discord_unlinked", "success"),
    ("discord", "taken"):    ("profile.discord_taken", "error"),
    ("discord", "expired"):  ("profile.discord_error", "error"),
    ("discord", "error"):    ("profile.discord_error", "error"),
}


def _notice(req, _):
    for (param, value), (key, kind) in NOTICES.items():
        if req.query_params.get(param) == value:
            return Div(_(key), cls=f"alert alert-{kind}", style="max-width:720px;")
    return None


def _verification_section(me, _):
    verified = me.get("is_verified")
    badge = Span(_("profile.verified") if verified else _("profile.not_verified"),
                 cls=f"badge {'badge-green' if verified else 'badge-amber'}")
    return Div(
        H3(_("profile.account_heading"), cls="card-title"),
        Div(
            Span(me.get("email", ""), style="font-weight:500;overflow-wrap:anywhere;"),
            badge,
            style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;",
        ),
        "" if verified else Div(
            P(_("profile.verify_hint"), style="margin:10px 0;"),
            Form(
                Button(_("profile.verify_send"), type="submit", cls="btn btn-secondary"),
                method="post", action="/profile/verify",
            ),
        ),
        cls="card", style="max-width:720px;margin-top:20px;",
    )


def _discord_section(me, _):
    discord = me.get("discord") or {}
    if not discord.get("available"):
        return None  # Discord login isn't configured on this server
    if discord.get("linked"):
        body = Div(
            P(_("profile.discord_connected_as"), " ",
              Strong(discord.get("username") or "Discord"), style="margin-bottom:10px;"),
            Form(
                Button(_("profile.discord_disconnect"), type="submit", cls="btn btn-secondary"),
                method="post", action="/profile/discord/disconnect",
            ),
        )
    else:
        body = Div(
            P(_("profile.discord_hint"), style="margin-bottom:10px;"),
            A(_("profile.discord_connect"), href="/profile/discord/connect", cls="btn btn-primary"),
        )
    return Div(
        H3(_("profile.discord_heading"), cls="card-title"),
        body,
        cls="card", style="max-width:720px;margin-top:20px;",
    )


def _stats_section(stats, _=None):
    _ = _ or (lambda k: k)
    return stats_section(stats, _)


def _content(me, _, stats=None, saved=False, error=None, notice=None):
    return Div(
        Div(H1(_("profile.heading")), cls="page-header"),
        notice,
        Form(
            _account_section(me, _, saved=saved, error=error),
            method="post", action="/profile",
            enctype="multipart/form-data",
            style="max-width:720px;"
        ),
        _verification_section(me, _),
        _discord_section(me, _),
        _stats_section(stats, _),
        Script("""
function previewAvatar(input) {
    if (input.files && input.files[0]) {
        var img = document.getElementById('avatar-preview');
        var reader = new FileReader();
        reader.onload = function (e) { img.src = e.target.result; };
        reader.readAsDataURL(input.files[0]);
        fmmCompressImage(input.files[0], 1024, 0.8).then(function (blob) {
            fmmSetFiles(input, blob, input.files[0].name.replace(/\\.[^.]+$/, '') + '.jpg');
        }).catch(function () {});
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

    if "token" in req.session:
        name = me.get("full_name") or me.get("username") or req.session.get("user_email", "")
        req.session["user_name"] = name
        req.session["user_username"] = me.get("username") or name
        req.session["user_avatar"] = me.get("avatar_key") or ""

    return page_shell(_content(me, _, stats=stats, notice=_notice(req, _)),
                      current="/profile", title=_("title.profile"), lang=lang)


@rt("/profile/verify")
async def post(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await profile_api.request_verification(token)
        result = "sent"
    except httpx.HTTPStatusError as e:
        result = "wait" if e.response.status_code == 429 else "error"
    except Exception:
        result = "error"
    return RedirectResponse(f"/profile?verify={result}", status_code=303)


@rt("/profile/discord/connect")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        url = await profile_api.discord_link_start(token)
    except Exception:
        return RedirectResponse("/profile?discord=error", status_code=302)
    return RedirectResponse(url, status_code=302)


@rt("/profile/discord/disconnect")
async def post(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await profile_api.discord_unlink(token)
        result = "unlinked"
    except Exception:
        result = "error"
    return RedirectResponse(f"/profile?discord={result}", status_code=303)


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
