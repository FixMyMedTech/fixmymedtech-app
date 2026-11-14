# pages/clinic_privacy.py — /groups/{org_id}/privacy, the clinic page's Privacy
# tab (clinic admins). Two switches decide what the profile of an engineer who
# registered the clinic's devices shows: the devices at all, and the clinic's
# name next to them ("a clinic" when hidden). The clinic's own pages always
# show its devices in full.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api
from features.onboarding.ui import ONBOARDING_CSS, clinic_tabs
from components import page_shell, alert
from i18n import t as make_t

rt = APIRouter()

PRIVACY_CSS = """
.switch-row{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;padding:16px 0;border-top:1px solid var(--border);}
.switch-row:first-of-type{border-top:none;}
.switch-row .s-text{flex:1;min-width:0;}
.switch-row .s-title{font-weight:600;color:var(--text);}
.switch-row .s-help{font-size:12px;color:var(--text-muted);margin-top:2px;}
.switch{position:relative;display:inline-block;width:44px;height:24px;flex-shrink:0;}
.switch input{opacity:0;width:0;height:0;}
.switch .knob{position:absolute;inset:0;cursor:pointer;background:var(--border-strong);border-radius:var(--radius-pill);transition:background .15s;}
.switch .knob::before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:var(--surface);border-radius:50%;transition:transform .15s;box-shadow:var(--shadow-card);}
.switch input:checked+.knob{background:var(--primary);}
.switch input:checked+.knob::before{transform:translateX(20px);}
.switch input:focus-visible+.knob{outline:2px solid var(--primary);outline-offset:2px;}
.switch input:disabled+.knob{opacity:.5;cursor:not-allowed;}
.preview{margin-top:8px;padding:12px 14px;background:var(--sunken);border-radius:var(--radius-control);font-size:14px;color:var(--text);}
"""


def _switch(name: str, checked: bool, title: str, help_text: str, disabled: bool = False):
    return Div(
        Div(Div(title, cls="s-title"), Div(help_text, cls="s-help"), cls="s-text"),
        Label(
            Input(type="checkbox", name=name, value="1", checked=checked, disabled=disabled,
                  onchange="this.form.submit()", aria_label=title),
            Span(cls="knob"),
            cls="switch",
        ),
        cls="switch-row",
    )


@rt("/groups/{org_id}/privacy")
async def get(req, org_id: str, saved: str = "", error: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        org = await ob_api.clinic_privacy(token, org_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse(f"/groups/{org_id}", status_code=302)

    show = org.get("show_devices_on_profiles", True)
    hide = org.get("hide_name_on_profiles", False)
    if not show:
        preview = _("privacy.preview_hidden")
    elif hide:
        preview = _("privacy.preview_anon")
    else:
        preview = _("privacy.preview_named").format(clinic=org.get("name", ""))

    form = Form(
        # Hidden "0"s so an unchecked box still sends its field.
        Input(type="hidden", name="show_devices_on_profiles", value="0"),
        Input(type="hidden", name="hide_name_on_profiles", value="0"),
        Input(type="hidden", name="hide_enabled", value="1" if show else "0"),
        _switch("show_devices_on_profiles", show, _("privacy.show_title"), _("privacy.show_help")),
        _switch("hide_name_on_profiles", hide, _("privacy.hide_title"), _("privacy.hide_help"), disabled=not show),
        Noscript(Button(_("privacy.save"), type="submit", cls="btn btn-primary btn-sm")),
        method="post", action=f"/groups/{org_id}/privacy",
    )

    content = Div(
        Style(ONBOARDING_CSS), Style(PRIVACY_CSS),
        A(_("groups.back_to_groups"), href="/groups",
          style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:inline-block;margin-bottom:16px;"),
        H1(org.get("name", "")),
        clinic_tabs(org_id, "privacy", _),
        alert(_("privacy.saved"), "success") if saved else "",
        alert(_("privacy.failed"), "error") if error else "",
        Div(
            H3(_("privacy.heading"), cls="card-title"),
            P(_("privacy.body"), style="color:var(--text-muted);margin-bottom:8px;"),
            form,
            Div(Div(_("privacy.preview_label"), cls="eyebrow", style="font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted);"),
                Div(preview, cls="preview")),
            cls="card", style="max-width:720px;",
        ),
    )
    return page_shell(content, current="/groups", title=org.get("name", ""), lang=lang)


@rt("/groups/{org_id}/privacy", methods=["post"])
async def post(req, org_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    # Each field arrives as the hidden "0" plus "1" when the box is checked.
    def _on(name):
        return "1" in form.getlist(name)
    data = {"show_devices_on_profiles": _on("show_devices_on_profiles")}
    # The name switch is disabled (sends nothing) while devices are hidden:
    # only save it when it was usable, so the stored choice survives.
    if form.get("hide_enabled") == "1" and data["show_devices_on_profiles"]:
        data["hide_name_on_profiles"] = _on("hide_name_on_profiles")
    try:
        await ob_api.update_clinic_privacy(token, org_id, data)
    except Exception:
        return RedirectResponse(f"/groups/{org_id}/privacy?error=1", status_code=303)
    return RedirectResponse(f"/groups/{org_id}/privacy?saved=1", status_code=303)
