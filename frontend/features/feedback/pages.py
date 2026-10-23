# pages.py — the feedback / issue form behind the floating "?" button.
#
# Open to everyone, logged in or not: the button is also on the public QR
# pages. The report goes to the backend, which stores it and posts it to the
# team's Discord forum as a new thread.

from fasthtml.common import *
import httpx

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.feedback.api as feedback_api

from components import pub_shell, alert

rt = APIRouter()

TYPES = ("feedback", "issue")


def _safe_page(value: str) -> str:
    """Keep only an in-app path, so the 'back' link can't point off-site."""
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//") and not value.startswith("/feedback"):
        return value[:500]
    return ""


SCREENSHOT_JS = """
function fbPreview(input){
  var img = document.getElementById('fb-shot-preview');
  if (!input.files || !input.files[0]) { img.style.display = 'none'; return; }
  var file = input.files[0];
  img.src = URL.createObjectURL(file);
  img.style.display = 'block';
  fmmCompressImage(file, 1600, 0.8).then(function (blob) {
    fmmSetFiles(input, blob, file.name.replace(/\\.[^.]+$/, '') + '.jpg');
  }).catch(function () {});
}
"""


def _form(_, lang: str, logged_in: bool, values: dict, error: str = ""):
    kind = values.get("type") if values.get("type") in TYPES else "feedback"
    type_choice = Div(
        *[Label(
            Input(type="radio", name="type", value=v, checked=(v == kind)),
            Span(_(f"feedback.type_{v}")),
            cls="fb-type",
        ) for v in TYPES],
        cls="fb-types",
    )
    return Div(
        Div(
            H2(_("feedback.heading"), style="margin-bottom:6px;"),
            P(_("feedback.intro"), style="margin-bottom:16px;"),
            alert(error),
            Form(
                type_choice,
                Div(
                    Label(_("feedback.summary_label"), cls="label", for_="fb-summary"),
                    Input(id="fb-summary", name="summary", cls="input", required=True,
                          maxlength="100", value=values.get("summary", ""),
                          placeholder=_("feedback.summary_placeholder")),
                    cls="form-group",
                ),
                Div(
                    Label(_("feedback.description_label"), cls="label", for_="fb-description"),
                    Textarea(values.get("description", ""), id="fb-description", name="description",
                             cls="input", rows="6", required=True, maxlength="4000",
                             placeholder=_("feedback.description_placeholder")),
                    cls="form-group",
                ),
                Div(
                    Label(_("feedback.screenshot_label"), cls="label", for_="fb-shot"),
                    Input(type="file", id="fb-shot", name="screenshot", accept="image/*",
                          cls="input", onchange="fbPreview(this)"),
                    Img(id="fb-shot-preview", alt="",
                        style="display:none;max-width:100%;max-height:200px;border-radius:8px;margin-top:10px;"),
                    cls="form-group",
                ),
                "" if logged_in else Div(
                    Label(_("feedback.contact_label"), cls="label", for_="fb-contact"),
                    Input(type="email", id="fb-contact", name="contact_email", cls="input",
                          maxlength="254", value=values.get("contact_email", "")),
                    P(_("feedback.contact_hint"), style="font-size:.78rem;margin-top:4px;"),
                    cls="form-group",
                ),
                # Honeypot: hidden from people, filled in by naive bots.
                Input(type="text", name="website", tabindex="-1", autocomplete="off",
                      aria_hidden="true", style="position:absolute;left:-9999px;"),
                Input(type="hidden", name="page", value=values.get("page", "")),
                Div(_("feedback.privacy_note"), cls="alert alert-warning", style="font-size:.8rem;"),
                Div(
                    # Back to the page the user came from, nothing is sent.
                    A(_("feedback.cancel"), href=values.get("page") or "/", cls="btn btn-secondary",
                      style="flex:1;justify-content:center;"),
                    Button(_("feedback.submit"), type="submit", cls="btn btn-primary",
                           style="flex:1;justify-content:center;"),
                    style="display:flex;gap:10px;",
                ),
                method="post", action="/feedback", enctype="multipart/form-data",
            ),
            Script(SCREENSHOT_JS),
            cls="card",
        ),
        cls="fb-page",
    )


@rt("/feedback")
async def get(req, type: str = "feedback", page: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    logged_in = bool(auth_helper.get_token(req))
    values = {"type": type, "page": _safe_page(page)}
    return pub_shell(_form(_, lang, logged_in, values), title=_("title.feedback"), lang=lang)


@rt("/feedback")
async def post(req):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    token = auth_helper.get_token(req)
    form = await req.form()
    values = {k: (form.get(k) or "") for k in ("type", "summary", "description", "contact_email")}
    values = {k: v.strip() if isinstance(v, str) else "" for k, v in values.items()}
    values["page"] = _safe_page(form.get("page") or "")

    if form.get("website"):
        # A bot filled the honeypot: pretend it worked, send nothing.
        return _done(_, lang, values["page"])

    if not values["summary"] or not values["description"]:
        return pub_shell(_form(_, lang, bool(token), values, _("feedback.error_required")),
                         title=_("title.feedback"), lang=lang)

    screenshot = None
    photo = form.get("screenshot")
    if photo is not None and getattr(photo, "filename", ""):
        content = await photo.read()
        if content:
            screenshot = (photo.filename, content, photo.content_type or "image/jpeg")

    data = {k: values[k] for k in ("type", "summary", "description", "page") if values[k]}
    data["lang"] = lang
    if not token and values["contact_email"]:
        data["contact_email"] = values["contact_email"]

    try:
        await feedback_api.submit_feedback(data, token, screenshot)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        # 4xx carries the backend's validation message; anything else is ours.
        msg = _("feedback.error_rate") if code == 429 else (str(e) if code < 500 else _("feedback.error_send"))
        return pub_shell(_form(_, lang, bool(token), values, msg),
                         title=_("title.feedback"), lang=lang)
    except Exception:
        return pub_shell(_form(_, lang, bool(token), values, _("feedback.error_send")),
                         title=_("title.feedback"), lang=lang)

    return _done(_, lang, values["page"])


def _done(_, lang: str, page: str):
    content = Div(
        Div(
            Div("✓", style="width:52px;height:52px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.3rem;display:flex;align-items:center;justify-content:center;margin:0 auto 14px;"),
            H2(_("feedback.success_heading")),
            P(_("feedback.success_msg")),
            A(_("feedback.back"), href=page or "/", cls="btn btn-secondary", style="margin-top:16px;"),
            style="text-align:center;padding:40px 24px;",
        ),
        cls="card",
    )
    return pub_shell(Div(content, cls="fb-page"), title=_("title.feedback"), lang=lang)
