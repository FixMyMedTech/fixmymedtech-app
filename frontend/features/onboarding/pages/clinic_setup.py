# pages/clinic_setup.py — a clinic account sets up its clinic.
#
#   /clinic/signup              a clinic signs up without an invitation
#   /clinic/setup               step 1: find the clinic on healthsites.io,
#                               nearest first (browser location or a city),
#                               or "my clinic isn't listed"
#   /clinic/setup/create        a clinic not on healthsites.io (flagged to be
#                               pushed there later)
#   /clinic/setup/profile       step 2: clinic profile, OK
#   /clinic/setup/engineers     step 3 (invited): confirm the inviting
#                               engineer, add more engineers
#   /clinic/setup/talk          step 3 (not invited): book the clinic talk
#
# Healthsites.io search and import are the backend's (routers/healthsites.py
# find_facilities, reused by /api/onboarding/clinic/*).

import httpx
from urllib.parse import quote
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.api as auth_api
import features.auth.helper as auth_helper
import features.groups.api as groups_api
import features.onboarding.api as ob_api
from features.onboarding.ui import ONBOARDING_CSS, setup_steps, error_detail
from components import page_shell, auth_shell, alert, status_badge
from i18n import t as make_t
import os

rt = APIRouter()

CLINIC_TYPES = ("clinic", "hospital", "health_centre", "lab")


def _type_options(_, selected="clinic"):
    return [Option(_(f"ob.type_{t}"), value=t, selected=(t == selected)) for t in CLINIC_TYPES]


async def _mine(token) -> dict:
    try:
        return await ob_api.clinic_mine(token)
    except Exception:
        return {"clinics": []}


def _shell(content, _, lang, title):
    return page_shell(Div(Style(ONBOARDING_CSS), content, style="max-width:760px;"),
                      current="/clinic/setup", title=title, lang=lang)


# ── Signup without invitation ───────────────────────────────────────────────

def _signup_page(req, _, error="", values=None):
    v = values or {}
    card = Div(
        Div(Span(Img(src=os.getenv("LOGO_URL") or "/static/fixmymedtech_africa.png",
                     style="height:56px;width:auto;display:block;margin-bottom:10px;"), cls="brand-icon"),
            H1(_("ob.clinic_signup_heading")), P(_("ob.clinic_signup_sub")), cls="auth-brand"),
        alert(error, "error"),
        Form(
            Div(Label(_("ob.clinic_signup_name"), cls="label", for_="full_name"),
                Input(id="full_name", name="full_name", required=True, cls="input", value=v.get("full_name", ""),
                      placeholder=_("signup.full_name_placeholder")), cls="form-group"),
            Div(Label(_("signup.email_label"), cls="label", for_="email"),
                Input(id="email", name="email", type="email", required=True, cls="input", value=v.get("email", ""),
                      placeholder=_("signup.email_placeholder")), cls="form-group"),
            Div(
                Div(Label(_("signup.password_label"), cls="label", for_="password"),
                    Input(id="password", name="password", type="password", required=True, minlength="8",
                          cls="input"), cls="form-group"),
                Div(Label(_("signup.confirm_label"), cls="label", for_="password2"),
                    Input(id="password2", name="password2", type="password", required=True, cls="input"),
                    cls="form-group"),
                cls="form-row"),
            Button(_("ob.clinic_signup_submit"), type="submit", cls="btn btn-primary", style="width:100%;margin-top:8px;"),
            method="post", action="/clinic/signup",
        ),
        P(_("ob.clinic_signup_engineer"), A(_("ob.clinic_signup_engineer_link"), href="/signup"),
          cls="auth-link", style="margin-top:12px;"),
        P(_("signup.login_link"), A(_("signup.login_link_action"), href="/login"), cls="auth-link"),
        cls="auth-card",
    )
    side = Div(Div(
        P(_("ob.clinic_signup_side1"), style="color:#fff;font-weight:500;"),
        P(_("ob.clinic_signup_side2"), style="color:rgba(255,255,255,.7);font-size:.9rem;"),
    ), cls="auth-bg")
    return auth_shell(Div(card, side, cls="auth-wrap"), title=_("ob.clinic_signup_heading"),
                      lang=req.session.get("lang", "en"))


@rt("/clinic/signup")
async def get(req):
    _ = make_t(req.session.get("lang", "en"))
    if auth_helper.get_token(req):
        return RedirectResponse("/clinic/setup", status_code=302)
    return _signup_page(req, _)


@rt("/clinic/signup")
async def post(req, full_name: str = "", email: str = "", password: str = "", password2: str = ""):
    _ = make_t(req.session.get("lang", "en"))
    error = ""
    if not full_name.strip():
        error = _("signup.error_name")
    elif not email.strip():
        error = _("signup.error_email")
    elif len(password) < 8:
        error = _("signup.error_password")
    elif password != password2:
        error = _("signup.error_mismatch")
    if not error:
        try:
            await auth_api.signup(email=email.strip(), password=password, full_name=full_name.strip(),
                                  account_kind="clinic")
            res = await auth_api.login(email.strip(), password)
            lang = req.session.get("lang", "en")
            req.session.clear()
            req.session["lang"] = lang
            req.session["token"] = res["access_token"]
            req.session["user_email"] = res["user"]["email"]
            return RedirectResponse("/clinic/setup", status_code=303)
        except httpx.HTTPStatusError as e:
            error = _("signup.already_heading") if error_detail(e) == "user_already_exists" else str(e)
        except Exception as e:
            error = str(e)
    return _signup_page(req, _, error, {"full_name": full_name, "email": email})


# ── Step 1: find the clinic ─────────────────────────────────────────────────

GEO_JS = """
function obUseLocation(btn) {
  if (!navigator.geolocation) { document.getElementById('ob-geo-err').hidden = false; return; }
  btn.disabled = true;
  navigator.geolocation.getCurrentPosition(function (pos) {
    location.href = '/clinic/setup?lat=' + pos.coords.latitude + '&lng=' + pos.coords.longitude;
  }, function () { btn.disabled = false; document.getElementById('ob-geo-err').hidden = false; });
}
"""


def _facility_form(_, f):
    hidden = [Input(type="hidden", name=k, value=str(f.get(k) or ""))
              for k in ("osm_id", "osm_type", "name", "country", "region", "address", "type")]
    dist = f.get("distance_km")
    return Li(
        Div(Strong(f.get("name", "")),
            Div(" · ".join(x for x in [f.get("address") or "", _("ob.km_away").format(km=dist) if dist is not None else ""] if x),
                cls="ob-muted")),
        Form(*hidden, Button(_("ob.this_is_my_clinic"), type="submit", cls="btn btn-primary btn-sm"),
             method="post", action="/clinic/setup/pick"),
    )


@rt("/clinic/setup")
async def get(req, lat: str = "", lng: str = "", q: str = "", error: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    me = await auth_helper.refresh_onboarding(req, token)
    if me.get("account_kind") != "clinic":
        return RedirectResponse("/getting-started", status_code=302)
    mine = await _mine(token)
    if mine.get("clinics") and not (lat or q):
        return RedirectResponse(f"/groups/{mine['clinics'][0]['id']}", status_code=302)
    invited = bool(mine.get("has_open_invitation"))

    results, search_error = None, ""
    if (lat and lng) or q.strip():
        try:
            data = await ob_api.clinic_search(token, float(lat), float(lng)) if lat and lng \
                else await ob_api.clinic_search(token, q=q.strip())
            results = data.get("facilities", [])
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            search_error = {503: _("ob.search_unavailable"), 404: _("ob.place_not_found")}.get(code, _("ob.search_failed"))
        except Exception:
            search_error = _("ob.search_failed")

    errors = {"has_admin": _("ob.clinic_has_admin"), "pick": _("ob.pick_failed")}
    content = Div(
        H1(_("ob.setup_heading")),
        setup_steps(1, _, invited),
        P(_("ob.find_intro"), style="color:var(--c-text-2);"),
        alert(errors.get(error, ""), "error"),
        Div(
            H3(_("ob.find_heading"), cls="card-title"),
            Div(Button(_("ob.use_location"), type="button", cls="btn btn-primary", onclick="obUseLocation(this)"),
                Span(_("ob.or"), cls="ob-muted"),
                Form(Input(name="q", value=q, cls="input", placeholder=_("ob.city_placeholder"),
                           style="max-width:240px;"),
                     Button(_("ob.search"), type="submit", cls="btn btn-secondary"),
                     method="get", action="/clinic/setup", style="display:flex;gap:8px;"),
                cls="ob-actions"),
            P(_("ob.geo_error"), id="ob-geo-err", hidden=True, cls="ob-muted", style="margin-top:8px;"),
            Script(GEO_JS),
            cls="card",
        ),
        Div(
            H3(_("ob.results_heading"), cls="card-title"),
            alert(search_error, "warning"),
            (Ul(*[_facility_form(_, f) for f in results], cls="ob-list") if results
             else P(_("ob.no_results"), cls="ob-muted")),
            cls="card", style="margin-top:16px;",
        ) if (results is not None or search_error) else "",
        Div(
            H3(_("ob.not_listed_heading"), cls="card-title"),
            P(_("ob.not_listed_body")),
            A(_("ob.not_listed_cta"), href="/clinic/setup/create", cls="btn btn-secondary"),
            cls="card", style="margin-top:16px;",
        ),
    )
    return _shell(content, _, lang, _("ob.setup_heading"))


@rt("/clinic/setup/pick")
async def post(req, osm_id: str = "", osm_type: str = "", name: str = "", country: str = "",
               region: str = "", address: str = "", type: str = "clinic"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        org = await ob_api.clinic_pick(token, {
            "osm_id": osm_id, "osm_type": osm_type, "name": name, "country": country,
            "region": region, "address": address, "type": type,
        })
    except httpx.HTTPStatusError as e:
        err = "has_admin" if error_detail(e) == "clinic_has_admin" else "pick"
        return RedirectResponse(f"/clinic/setup?error={err}", status_code=303)
    except Exception:
        return RedirectResponse("/clinic/setup?error=pick", status_code=303)
    req.session["user_clinic_ready"] = "1"
    return RedirectResponse(f"/clinic/setup/profile?org={org['id']}", status_code=303)


@rt("/clinic/setup/create")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    mine = await _mine(token)
    content = Div(
        H1(_("ob.setup_heading")),
        setup_steps(1, _, bool(mine.get("has_open_invitation"))),
        Div(
            H3(_("ob.create_heading"), cls="card-title"),
            P(_("ob.create_body"), cls="ob-muted"),
            Form(
                Div(Label(_("ob.clinic_name"), cls="label", for_="name"),
                    Input(id="name", name="name", required=True, cls="input"), cls="form-group"),
                Div(Div(Label(_("ob.clinic_country"), cls="label", for_="country"),
                        Input(id="country", name="country", cls="input"), cls="form-group"),
                    Div(Label(_("ob.clinic_region"), cls="label", for_="region"),
                        Input(id="region", name="region", cls="input"), cls="form-group"),
                    cls="form-row"),
                Div(Label(_("ob.clinic_address"), cls="label", for_="address"),
                    Input(id="address", name="address", cls="input"), cls="form-group"),
                Div(Label(_("ob.clinic_type"), cls="label", for_="type"),
                    Select(*_type_options(_), id="type", name="type", cls="input"), cls="form-group"),
                Div(A(_("ob.back"), href="/clinic/setup", cls="btn btn-secondary"),
                    Button(_("ob.create_submit"), type="submit", cls="btn btn-primary"), cls="ob-actions"),
                method="post", action="/clinic/setup/create",
            ),
            cls="card",
        ),
    )
    return _shell(content, _, lang, _("ob.setup_heading"))


@rt("/clinic/setup/create")
async def post(req, name: str = "", country: str = "", region: str = "", address: str = "",
               type: str = "clinic"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    if not name.strip():
        return RedirectResponse("/clinic/setup/create", status_code=303)
    try:
        org = await ob_api.clinic_create(token, {
            "name": name.strip(), "country": country.strip(), "region": region.strip(),
            "address": address.strip(), "type": type,
        })
    except Exception:
        return RedirectResponse("/clinic/setup?error=pick", status_code=303)
    req.session["user_clinic_ready"] = "1"
    return RedirectResponse(f"/clinic/setup/profile?org={org['id']}", status_code=303)


# ── Step 2: clinic profile ──────────────────────────────────────────────────

async def _my_clinic(token, org_id):
    mine = await _mine(token)
    for c in mine.get("clinics", []):
        if c["id"] == org_id:
            return c, mine
    return None, mine


@rt("/clinic/setup/profile")
async def get(req, org: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    clinic, mine = await _my_clinic(token, org)
    if clinic is None:
        return RedirectResponse("/clinic/setup", status_code=302)
    invited = bool(clinic.get("inviter"))
    content = Div(
        H1(_("ob.setup_heading")),
        setup_steps(2, _, invited),
        Div(
            H3(_("ob.profile_heading"), cls="card-title"),
            P(_("ob.profile_body"), cls="ob-muted"),
            P(_("ob.flagged_push"), cls="ob-muted") if clinic.get("push_to_healthsites") else "",
            Form(
                Div(Label(_("ob.clinic_name"), cls="label", for_="name"),
                    Input(id="name", name="name", required=True, cls="input", value=clinic.get("name") or ""),
                    cls="form-group"),
                Div(Div(Label(_("ob.clinic_country"), cls="label", for_="country"),
                        Input(id="country", name="country", cls="input", value=clinic.get("country") or ""),
                        cls="form-group"),
                    Div(Label(_("ob.clinic_region"), cls="label", for_="region"),
                        Input(id="region", name="region", cls="input", value=clinic.get("region") or ""),
                        cls="form-group"),
                    cls="form-row"),
                Div(Label(_("ob.clinic_address"), cls="label", for_="address"),
                    Input(id="address", name="address", cls="input", value=clinic.get("address") or ""),
                    cls="form-group"),
                Div(Div(Label(_("ob.clinic_contact"), cls="label", for_="contact_email"),
                        Input(id="contact_email", name="contact_email", type="email", cls="input",
                              value=clinic.get("contact_email") or ""), cls="form-group"),
                    Div(Label(_("ob.clinic_type"), cls="label", for_="type"),
                        Select(*_type_options(_, clinic.get("type") or "clinic"), id="type", name="type",
                               cls="input"), cls="form-group"),
                    cls="form-row"),
                Input(type="hidden", name="org", value=org),
                Button(_("ob.ok"), type="submit", cls="btn btn-primary"),
                method="post", action="/clinic/setup/profile",
            ),
            cls="card",
        ),
    )
    return _shell(content, _, lang, _("ob.setup_heading"))


@rt("/clinic/setup/profile")
async def post(req, org: str = "", name: str = "", country: str = "", region: str = "", address: str = "",
               contact_email: str = "", type: str = "clinic"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    clinic, _mine_ = await _my_clinic(token, org)
    if clinic is None:
        return RedirectResponse("/clinic/setup", status_code=303)
    data = {"country": country.strip(), "region": region.strip(), "address": address.strip(),
            "contact_email": contact_email.strip(), "type": type if type in CLINIC_TYPES else "clinic"}
    if name.strip():
        data["name"] = name.strip()
    try:
        await groups_api.update_organization(token, org, data)
    except Exception:
        pass
    await auth_helper.refresh_onboarding(req, token)
    nxt = "engineers" if clinic.get("inviter") else "talk"
    return RedirectResponse(f"/clinic/setup/{nxt}?org={org}", status_code=303)


# ── Step 3a: responsible engineers (invited clinic) ─────────────────────────

def add_engineer_form(_, action: str, org: str = ""):
    return Form(
        Div(Div(Label(_("ob.add_engineer_email"), cls="label", for_="eng-email"),
                Input(id="eng-email", name="email", type="email", required=True, cls="input",
                      placeholder=_("ob.invite_email_placeholder")), cls="form-group"),
            Div(Label(_("ob.add_engineer_kind"), cls="label", for_="eng-kind"),
                Select(Option(_("ob.kind_external"), value="external"),
                       Option(_("ob.kind_internal"), value="internal"),
                       id="eng-kind", name="kind", cls="input"), cls="form-group"),
            cls="form-row"),
        Input(type="hidden", name="org", value=org) if org else "",
        Button(_("ob.add_engineer_submit"), type="submit", cls="btn btn-secondary"),
        method="post", action=action,
    )


@rt("/clinic/setup/engineers")
async def get(req, org: str = "", added: str = "", error: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    clinic, _m = await _my_clinic(token, org)
    if clinic is None:
        return RedirectResponse("/clinic/setup", status_code=302)
    inviter = clinic.get("inviter") or {}
    try:
        engineers = (await ob_api.clinic_engineers(token, org)).get("engineers", [])
    except Exception:
        engineers = []
    others = [e for e in engineers if e["id"] != inviter.get("id")]

    question = Div(
        H3(_("ob.confirm_question").format(engineer=inviter.get("name", ""), clinic=clinic.get("name", "")),
           cls="card-title"),
        P(_("ob.confirm_explain")),
        (Div(status_badge("confirmed", "invitation"), P(_("ob.confirmed_note"), cls="ob-muted"))
         if inviter.get("status") == "confirmed" else
         Div(Form(Input(type="hidden", name="org", value=org), Input(type="hidden", name="answer", value="yes"),
                  Button(_("ob.answer_yes"), type="submit", cls="btn btn-primary"),
                  method="post", action="/clinic/setup/engineers/answer"),
             Form(Input(type="hidden", name="org", value=org), Input(type="hidden", name="answer", value="not_now"),
                  Button(_("ob.answer_not_now"), type="submit", cls="btn btn-secondary"),
                  method="post", action="/clinic/setup/engineers/answer"),
             cls="ob-actions")),
        cls="card",
    ) if inviter else ""

    added_list = Ul(*[Li(Span(e["name"] or e["email"]), status_badge(e["status"], "engineer")) for e in others],
                    cls="ob-list") if others else ""
    content = Div(
        H1(_("ob.setup_heading")),
        setup_steps(3, _, True),
        question,
        Div(
            H3(_("ob.add_engineer_heading"), cls="card-title"),
            P(_("ob.add_engineer_body"), cls="ob-muted"),
            alert(_("ob.engineer_added").format(email=added), "success") if added else "",
            alert(_("ob.engineer_add_failed"), "error") if error else "",
            added_list,
            add_engineer_form(_, "/clinic/setup/engineers/add", org),
            cls="card", style="margin-top:16px;",
        ),
        Div(A(_("ob.finish"), href=f"/groups/{org}/engineers", cls="btn btn-primary"),
            style="margin-top:16px;"),
    )
    return _shell(content, _, lang, _("ob.setup_heading"))


@rt("/clinic/setup/engineers/answer")
async def post(req, org: str = "", answer: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    clinic, _m = await _my_clinic(token, org)
    inviter = (clinic or {}).get("inviter") or {}
    if inviter.get("id"):
        try:
            if answer == "yes":
                await ob_api.confirm_engineer(token, org, inviter["id"])
            else:
                await ob_api.not_now_engineer(token, org, inviter["id"])
        except Exception:
            pass
    return RedirectResponse(f"/clinic/setup/engineers?org={org}", status_code=303)


@rt("/clinic/setup/engineers/add")
async def post(req, org: str = "", email: str = "", kind: str = "external"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await ob_api.add_engineer(token, org, email.strip(), kind)
        return RedirectResponse(f"/clinic/setup/engineers?org={org}&added={quote(email.strip())}", status_code=303)
    except Exception:
        return RedirectResponse(f"/clinic/setup/engineers?org={org}&error=1", status_code=303)


# ── Step 3b: clinic talk (clinic that came without an invitation) ───────────

@rt("/clinic/setup/talk")
async def get(req, org: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    clinic, mine = await _my_clinic(token, org)
    if clinic is None:
        return RedirectResponse("/clinic/setup", status_code=302)
    booking = (mine.get("links") or {}).get("clinic_talk_booking") or ""
    content = Div(
        H1(_("ob.setup_heading")),
        setup_steps(3, _, False),
        Div(
            H3(_("ob.talk_heading"), cls="card-title"),
            P(_("ob.talk_body")),
            P(_("ob.talk_locked")),
            Div(status_badge(clinic.get("clinic_status", ""), "clinic"), style="margin-bottom:12px;"),
            (A(_("ob.talk_book"), href=booking, target="_blank", rel="noopener", cls="btn btn-primary")
             if booking else P(_("ob.talk_no_link"), cls="ob-muted")),
            cls="card ob-next",
        ),
        Div(A(_("ob.finish"), href=f"/groups/{org}/engineers", cls="btn btn-secondary"),
            style="margin-top:16px;"),
    )
    return _shell(content, _, lang, _("ob.setup_heading"))
