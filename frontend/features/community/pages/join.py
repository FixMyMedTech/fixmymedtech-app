# /join — the one way into the community (replaces /signup).
#
# Creates the account straight away and signs the person in. The account is a
# community applicant: it only sees /community/start until the welcome quests
# are done. /join?ref=<username> credits the member who shared the link.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
import features.profile.api as profile_api
from components import auth_shell
from features.community.ui import country_select, error_detail
from i18n import t as make_t

rt = APIRouter()

KINDS = ("engineer", "student", "clinician", "other")


def _field(label, control, for_):
    return Div(Label(label, cls="label", for_=for_), control, cls="form-group")


def _form(_, values=None, errors=None, ref=""):
    v = values or {}
    kind = v.get("kind") or "engineer"
    return Form(
        Div(
            Div(
                H1(_("cj.join.title")),
                P(_("cj.join.subtitle")),
                cls="cj-hero",
            ),
            *[Div(e, cls="alert alert-error", role="alert") for e in (errors or [])],
            _field(_("cj.join.full_name"), Input(id="full_name", name="full_name", cls="input", required=True,
                                                 autocomplete="name", value=v.get("full_name", "")), "full_name"),
            Div(
                _field(_("cj.join.email"), Input(id="email", name="email", type="email", cls="input", required=True,
                                                 autocomplete="email", value=v.get("email", "")), "email"),
                _field(_("cj.join.password"), Input(id="password", name="password", type="password", cls="input",
                                                    required=True, minlength="8", autocomplete="new-password"),
                       "password"),
                cls="form-row",
            ),
            Div(
                _field(_("cj.join.country"), country_select("country", v.get("country", ""), _, required=True), "country"),
                _field(_("cj.join.city"), Input(id="city", name="city", cls="input", required=True,
                                                value=v.get("city", "")), "city"),
                cls="form-row",
            ),
            Fieldset(
                Legend(_("cj.join.kind"), cls="label"),
                Div(*[Label(Input(type="radio", name="kind", value=k, checked=(k == kind)), _(f"cj.kind.{k}"),
                            cls="cj-choice") for k in KINDS], cls="cj-pills"),
                style="border:0;margin:0 0 14px;padding:0;",
            ),
            Div(
                _field(_("cj.join.organisation"), Input(id="organisation", name="organisation", cls="input",
                                                        value=v.get("organisation", "")), "organisation"),
                _field(_("cj.join.country_trained"), country_select("country_trained", v.get("country_trained", ""), _),
                       "country_trained"),
                cls="form-row",
            ),
            _field(_("cj.join.motivation"), Textarea(v.get("motivation", ""), id="motivation", name="motivation",
                                                     rows="3", cls="input", maxlength="1000"), "motivation"),
            _field(_("cj.join.heard_from"), Input(id="heard_from", name="heard_from", cls="input",
                                                  value=v.get("heard_from", "")), "heard_from"),
            Label(Input(type="checkbox", name="contact_ok", value="1", required=True,
                        checked=bool(v.get("contact_ok"))),
                  Span(_("cj.join.contact_ok")),
                  style="display:flex;gap:8px;align-items:flex-start;font-size:12px;color:var(--text-muted);margin-bottom:14px;"),
            Input(type="hidden", name="ref", value=ref),
            Button(_("cj.join.submit"), type="submit", cls="btn btn-primary", style="width:100%;min-height:44px;"),
            P(_("cj.join.have_account"), " ", A(_("cj.join.login"), href="/login"),
              cls="cj-small", style="text-align:center;margin-top:12px;"),
            cls="cj cj-narrow cj-card", style="margin:40px auto;",
        ),
        method="post", action="/join",
    )


@rt("/join")
async def get(req, ref: str = ""):
    if auth_helper.get_token(req):
        return RedirectResponse("/home", status_code=302)
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    return auth_shell(Div(_form(_, ref=ref), style="padding:0 16px;"), title=_("cj.title.join"), lang=lang)


@rt("/join")
async def post(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    form = await req.form()
    v = {k: (form.get(k) or "").strip() for k in (
        "full_name", "email", "country", "city", "kind", "organisation", "country_trained",
        "motivation", "heard_from", "ref", "contact_ok")}
    password = form.get("password") or ""
    errors = []
    if not v["full_name"]:
        errors.append(_("cj.join.error_name"))
    if not v["email"]:
        errors.append(_("cj.join.error_email"))
    if len(password) < 8:
        errors.append(_("cj.join.error_password"))
    if not v["country"] or not v["city"]:
        errors.append(_("cj.join.error_place"))
    if v["kind"] not in KINDS:
        v["kind"] = "other"
    if not v["contact_ok"]:
        errors.append(_("cj.join.error_contact"))

    if not errors:
        payload = {k: v[k] or None for k in ("full_name", "email", "country", "city", "kind", "organisation",
                                             "country_trained", "motivation", "heard_from", "ref")}
        payload["password"] = password
        try:
            res = await community_api.join(payload)
            req.session["token"] = res["access_token"]
            req.session["user_email"] = res["user"]["email"]
            try:
                auth_helper.store_me(req, await profile_api.get_me(res["access_token"]))
            except Exception:
                req.session["member_status"] = "applicant"
            return RedirectResponse("/community/start?joined=1", status_code=303)
        except httpx.HTTPStatusError as e:
            detail = error_detail(e)
            if detail == "user_already_exists":
                errors.append(_("cj.join.error_exists"))
            else:
                errors.append(_("cj.join.error_generic"))
        except Exception:
            errors.append(_("cj.join.error_generic"))

    return auth_shell(Div(_form(_, values=v, errors=errors, ref=v.get("ref", "")), style="padding:0 16px;"),
                      title=_("cj.title.join"), lang=lang)
