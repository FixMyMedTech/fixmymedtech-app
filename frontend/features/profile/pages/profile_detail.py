# pages/profile_detail.py — read-only view of ANOTHER user's profile.
#
# Reached from the "Registered by" link on a device. Deliberately has no form,
# no inputs and no save button: it renders, it never mutates.
# Your own profile lives in my_profile; if the id resolves to you we redirect
# there instead of showing yourself a locked page.

from fasthtml.common import *
from starlette.responses import RedirectResponse, Response
import features.profile.api as profile_api
import features.auth.helper as auth_helper
from i18n import t as make_t
from components import page_shell, AVATAR_IMG_STYLE, TRANSPARENT_GIF, stats_section

rt = APIRouter()


def _role_label(role, _):
    key = {"clinical_staff": "signup.role_clinical"}.get(role, f"role.{role}")
    label = _(key)
    return role if label == key else label


def _view_error(_, heading, message):
    return Div(
        Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
        H2(heading),
        P(message, style="color:var(--c-text-3);"),
        A(_("profile.view_back"), href="/devices", cls="btn btn-secondary",
          style="margin-top:16px;"),
        style="text-align:center;padding:60px 24px;",
    )


def _view_content(p, _, back=""):
    # Arriving from the Network directory we return there, preserving the
    # view and ordering the member had chosen; from a device's "Registered by"
    # link we return to the device list. `back` is a full path so the network
    # page's query string survives the round-trip.
    if back == "network":
        back = "/network"
    from_network = back.startswith("/network")
    back_href = back if from_network else "/devices"
    back_label = _("network.heading") if from_network else _("profile.view_back")

    avatar_key = p.get("avatar_key", "") or ""
    src = f"/profile/{p.get('id')}/photo?v={avatar_key}" if avatar_key else TRANSPARENT_GIF
    full_name = p.get("full_name") or ""
    username = p.get("username") or ""
    orgs = p.get("organizations") or []

    def _field(label, value):
        return Div(
            Div(label, cls="own-label"),
            Div(value or _("common.fallback"), cls="own-name"),
            cls="own-col",
        )

    org_cards = []
    for o in orgs:
        name = o.get("name") or _("common.fallback")
        oid = o.get("id")
        role = _role_label(o.get("role"), _) if o.get("role") else None
        org_cards.append(Div(
            Div(
                A(name, href=f"/groups/{oid}/view",
                  style="color:var(--c-primary);text-decoration:none;") if oid else name,
                cls="own-name",
            ),
            Div(role, cls="own-label") if role else "",
            cls="own-col",
        ))

    return Div(
        Div(
            Div(
                H1(full_name or username or _("profile.view_heading")),
                P(f"@{username}" if username else "",
                  style="color:var(--c-text-3);") if username else "",
            ),
            A(back_label, href=back_href, cls="btn btn-secondary btn-sm"),
            cls="page-header",
        ),
        Div(
            Img(src=src, alt="", style=AVATAR_IMG_STYLE),
            Div(
                _field(_("profile.full_name_label"), full_name),
                _field(_("profile.username_label"), username),
                _field(_("profile.country_label"), p.get("country") or ""),
                cls="own-grid",
                style="flex:1;min-width:0;",
            ),
            cls="card profile-basic",
            style="max-width:720px;margin-bottom:16px;",
        ),
        # The same four numbers as their row in the Network directory.
        stats_section(p, _, style="max-width:720px;margin-bottom:16px;"),
        Div(
            H3(_("profile.orgs_heading"), cls="card-title"),
            Div(*org_cards, cls="own-grid") if org_cards
            else P(_("profile.orgs_empty"),
                   style="color:var(--c-text-3);font-size:.875rem;margin:0;"),
            cls="card",
            style="max-width:720px;",
        ),
    )


@rt("/profile/{profile_id}")
async def get_view(req, profile_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    title = _("profile.view_heading")
    # `back` is either a full path (/network?view=table&sort=devices) or the
    # legacy "network" sentinel still present in older links.
    raw_back = req.query_params.get("back", "")
    back = "/network" if raw_back == "network" else raw_back
    current = "/network" if back.startswith("/network") else "/devices"

    try:
        p = await profile_api.get_profile(token, profile_id)
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", 0)
        if status == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        message = _("profile.view_denied") if status == 403 else _("profile.view_missing")
        return page_shell(_view_error(_, title, message),
                          current=current, title=title, lang=lang)

    # This route is strictly "someone else's profile". Your own lives at
    # /profile (editable), so never render the read-only page for yourself.
    if p.get("is_self"):
        return RedirectResponse("/profile", status_code=302)

    return page_shell(_view_content(p, _, back=back),
                      current=current, title=title, lang=lang)


@rt("/profile/{profile_id}/photo")
async def get_view_photo(req, profile_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        content, ctype = await profile_api.get_profile_photo(token, profile_id)
        return Response(content=content, media_type=ctype)
    except Exception:
        return Response(status_code=404)
