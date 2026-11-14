# /community/admin/teams — the three teams and the achievements they recognise.
#
# Anyone signed in can read this page. A team's lead (or a superuser) gets an
# edit form for that team: name, description, LinkedIn title and the list of
# tasks, in each language. Achievement levels are edited in SQLAdmin.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell
from features.community.ui import (
    admin_tabs, name_of, text_of, tasks_of, flash, error_detail, perms,
)
from i18n import t as make_t

rt = APIRouter()

LANGS = (("en", "English"), ("fr", "Français"), ("es", "Español"))


def _team_card(team: dict, achievements: list, editable: bool, lang: str, _):
    counts = team.get("counts") or {}
    mine = [a for a in achievements if a.get("team_key") == team["key"]]
    return Div(
        Div(H2(name_of(team, lang)),
            Span(_("cj.map.team_counts").format(members=counts.get("member", 0) + counts.get("lead", 0),
                                                candidates=counts.get("candidate", 0)), cls="cj-small"),
            cls="cj-between"),
        P(text_of(team, "descriptions", lang)),
        Ul(*[Li(x) for x in tasks_of(team, lang)], style="margin:0;padding-left:18px;line-height:1.7;"),
        P(Strong(_("cj.teams.linkedin")), " ", text_of(team, "linkedin_titles", lang) or "—", cls="cj-small"),
        P(Strong(_("cj.map.team_achievements") + ":"), " ",
          ", ".join(name_of(a, lang) for a in mine) or _("cj.map.team_no_achievements"), cls="cj-small"),
        Div(A(_("cj.teams.open_map"), href=f"/community/achievements?sel=team:{team['key']}#cj-panel",
              cls="btn btn-secondary btn-sm"),
            A(_("cj.teams.edit"), href=f"?edit={team['key']}#edit", cls="btn btn-primary btn-sm")
            if editable else "",
            cls="cj-row"),
        cls="cj-card",
    )


def _edit_form(team: dict, _):
    fields = []
    for code, label in LANGS:
        fields.append(Fieldset(
            Legend(label),
            Div(Label(_("cj.teams.name"), cls="label", for_=f"names_{code}"),
                Input(id=f"names_{code}", name=f"names_{code}", value=(team.get("names") or {}).get(code, ""),
                      cls="input", required=(code == "en"), maxlength="100"), cls="form-group"),
            Div(Label(_("cj.teams.description"), cls="label", for_=f"descriptions_{code}"),
                Textarea((team.get("descriptions") or {}).get(code, ""), id=f"descriptions_{code}",
                         name=f"descriptions_{code}", cls="input", rows="2", maxlength="1000"), cls="form-group"),
            Div(Label(_("cj.teams.linkedin"), cls="label", for_=f"linkedin_titles_{code}"),
                Input(id=f"linkedin_titles_{code}", name=f"linkedin_titles_{code}",
                      value=(team.get("linkedin_titles") or {}).get(code, ""), cls="input", maxlength="200"),
                cls="form-group"),
            Div(Label(_("cj.teams.tasks"), cls="label", for_=f"tasks_{code}"),
                Textarea("\n".join((team.get("tasks") or {}).get(code) or []), id=f"tasks_{code}",
                         name=f"tasks_{code}", cls="input", rows="6"),
                Span(_("cj.teams.tasks_help"), cls="cj-small"), cls="form-group"),
            style="border:1px solid var(--border);border-radius:var(--radius-md,8px);padding:12px;margin:0;",
        ))
    return Form(
        H2(_("cj.teams.edit_title").format(team=name_of(team, "en"))),
        *fields,
        Div(Button(_("cj.save"), type="submit", cls="btn btn-primary"),
            A(_("cj.cancel"), href="/community/admin/teams", cls="btn btn-secondary"), cls="cj-row"),
        method="post", action=f"/community/admin/teams/{team['key']}", id="edit",
        cls="cj-card is-focus",
    )


def _achievement_table(achievements: list, teams: dict, lang: str, _):
    rows = [Tr(
        Td(name_of(a, lang)),
        Td(name_of(teams.get(a.get("team_key")), lang)),
        Td(_("cj.map.counted_auto") if a.get("source") == "metric"
           else _("cj.map.recognised_by").format(team=name_of(teams.get(a.get("team_key")), lang))),
        Td(" · ".join(str(n) for n in a.get("levels") or []), style="white-space:nowrap;"),
    ) for a in achievements]
    return Div(
        H2(_("cj.teams.achievements_title")),
        P(_("cj.teams.levels_note"), cls="cj-small"),
        Div(Table(Thead(Tr(*[Th(_(k), scope="col") for k in (
            "cj.admin.achievement", "cj.map.team", "cj.teams.col_how", "cj.map.levels")])),
            Tbody(*rows), cls="cj-table"), cls="cj-tablewrap"),
        cls="cj-card",
    )


@rt("/community/admin/teams")
async def get(req, edit: str = "", msg: str = "", err: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        cat = await community_api.get_catalogue()
    except Exception:
        return page_shell(Div(flash(_("cj.error.load"), "error"), cls="cj"), current="/community/admin",
                          title=_("cj.title.admin"), lang=lang)
    mine = perms(req)
    teams = cat.get("teams") or []
    achievements = cat.get("achievements") or []
    by_key = {t["key"]: t for t in teams}
    editing = by_key.get(edit) if f"edit_team:{edit}" in mine else None

    content = Div(
        Div(H1(_("cj.admin.title")), cls="cj-between"),
        admin_tabs("teams", req, _),
        flash(_("cj.teams.saved")) if msg == "saved" else "",
        flash(_(f"cj.error.{err}", err), "error") if err else "",
        P(_("cj.teams.intro")),
        _edit_form(editing, _) if editing else "",
        Div(*[_team_card(t, achievements, f"edit_team:{t['key']}" in mine, lang, _) for t in teams],
            cls="cj-grid"),
        _achievement_table(achievements, by_key, lang, _),
        cls="cj",
    )
    return page_shell(content, current="/community/admin", title=_("cj.title.admin"), lang=lang)


@rt("/community/admin/teams/{key}")
async def post(req, key: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    data = {field: {code: (form.get(f"{field}_{code}") or "").strip() for code, _l in LANGS}
            for field in ("names", "descriptions", "linkedin_titles")}
    data["tasks"] = {code: [x.strip() for x in (form.get(f"tasks_{code}") or "").splitlines() if x.strip()]
                     for code, _l in LANGS}
    try:
        await community_api.edit_team(token, key, data)
    except httpx.HTTPStatusError as e:
        return RedirectResponse(f"/community/admin/teams?edit={key}&err={error_detail(e)}#edit", status_code=303)
    except Exception:
        return RedirectResponse(f"/community/admin/teams?edit={key}&err=save#edit", status_code=303)
    return RedirectResponse("/community/admin/teams?msg=saved", status_code=303)
