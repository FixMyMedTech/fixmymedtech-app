# /community/roles/{key} — one role: what it does, how to unlock it, what it
# unlocks, its LinkedIn title, and a Claim button for open roles.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell, pub_shell
from features.community.ui import (
    role_name, role_text, requirement_list, flash, refresh_session, error_detail,
)
from i18n import t as make_t

rt = APIRouter()


@rt("/community/roles/{key}")
async def get(req, key: str, claimed: str = "", err: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    token = auth_helper.get_token(req)
    try:
        tree = await community_api.get_tree()
    except Exception:
        tree = {"roles": [], "permissions": {}}
    roles_by_key = {r["key"]: r for r in tree.get("roles") or []}
    role = roles_by_key.get(key)
    shell = (lambda c, **kw: page_shell(c, current="/community/tree", **kw)) if token else pub_shell
    if not role:
        return shell(Div(flash(_("cj.role.not_found"), "error"), cls="cj"), title=_("cj.title.tree"), lang=lang)

    me = None
    if token:
        try:
            me = await community_api.get_me(token)
        except Exception:
            me = None
    state = (me or {}).get("progress", {}).get(key) if me else None
    reqs = state["requirements"] if state else role.get("requirements", [])
    held = bool(state and state.get("held"))
    perms_desc = tree.get("permissions") or {}

    claim = ""
    if me and role["unlock"] == "claim" and not held and me.get("member_status") == "member":
        if state and state.get("ready"):
            team_select = ""
            if role["scope"] == "global":
                team_select = Div(
                    Label(_("cj.role.choose_team"), cls="label", for_="team"),
                    Select(*[Option(_(f"cj.team.{t}"), value=t) for t in tree.get("teams", [])],
                           name="team", id="team", cls="input"),
                    cls="form-group")
            claim = Form(team_select,
                         Button(_("cj.role.claim").format(role=role_name(role, lang)), type="submit",
                                cls="btn btn-primary"),
                         method="post", action=f"/community/roles/{key}/claim")
        else:
            claim = P(_("cj.role.claim_when_ready"))

    status_badge = ""
    if held:
        status_badge = Span(_("cj.state.held"), cls="badge badge-ok")
    elif state:
        status_badge = Span(_("cj.role.progress").format(met=state["met"], total=state["total"]), cls="badge badge-neutral")

    content = Div(
        A(_("cj.role.back"), href="/community/tree", cls="cj-small"),
        Div(
            Span(_("cj.path." + role["path"]) + " · " + _("cj.tier").format(n=role["tier"]), cls="cj-eyebrow"),
            Div(H1(role_name(role, lang)), status_badge, cls="cj-between"),
            P(role_text(role, "descriptions", lang)),
            Div(Span(_("cj.role.holders").format(n=role.get("holders", 0)), cls="cj-small"),
                Span(_("cj.unlock." + role["unlock"] + ".long"), cls="cj-small"), cls="cj-row"),
            claim,
            cls="cj-card",
        ),
        flash(_("cj.role.claimed")) if claimed else "",
        flash(_(f"cj.error.{err}", _("cj.error.save")), "error") if err else "",
        Div(
            Div(H2(_("cj.role.how_to_unlock")), cls="cj-between"),
            requirement_list(reqs, roles_by_key, _, lang, show_progress=bool(state)),
            P(_("cj.role.assigned_note")) if role["unlock"] == "assigned" else "",
            cls="cj-card",
        ),
        Div(
            H2(_("cj.role.what_it_unlocks")),
            Ul(*[Li(_(f"cj.perm.{p}", perms_desc.get(p, {}).get("en", p))) for p in role.get("permissions", [])],
               style="margin:0;padding-left:20px;color:var(--text);line-height:1.8;")
            if role.get("permissions") else P(_("cj.role.no_permissions")),
            cls="cj-card",
        ),
        Div(
            H3(_("cj.role.linkedin")),
            P(role_text(role, "linkedin_titles", lang), style="color:var(--text);font-weight:500;"),
            Span(_("cj.role.linkedin_help"), cls="cj-small"),
            cls="cj-card",
        ),
        cls="cj cj-narrow",
    )
    return shell(content, title=f"{role_name(role, lang)} — FixMyMedTech", lang=lang)


@rt("/community/roles/{key}/claim")
async def post(req, key: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    try:
        await community_api.claim_role(token, key, form.get("team") or None)
    except httpx.HTTPStatusError as e:
        return RedirectResponse(f"/community/roles/{key}?err={error_detail(e)}", status_code=303)
    except Exception:
        return RedirectResponse(f"/community/roles/{key}?err=save", status_code=303)
    await refresh_session(req, token)
    return RedirectResponse(f"/community/roles/{key}?claimed=1", status_code=303)
