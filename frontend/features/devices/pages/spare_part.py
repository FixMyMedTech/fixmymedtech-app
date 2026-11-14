# features/devices/pages/spare_part.py — wave 3, the spare-part post helper.
#
# /device/{id}/spare-part writes a ready-to-paste "spare part needed" post
# for WhatsApp groups or the country's Discord channel. It is prefilled from
# the device (type, brand, model, year) and the clinic's region and country;
# the engineer adds the part, its markings, the quantity and the urgency.
# The clinic's name is never put in the post (only city and country), as
# agreed for spare-part requests. Nothing is stored: the post is built in the
# browser and copied or shared.

import json

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.devices.api as devices_api
from components import page_shell, page_head
from features.devices.static.guides import category_label
from i18n import t as make_t

rt = APIRouter()

SPARE_CSS = """
.spare{max-width:760px;}
.spare .muted{color:var(--text-muted);font-size:14px;}
.spare-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
.spare .field label{display:block;font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:4px;}
.spare .full{grid-column:1/-1;}
.urg{display:flex;flex-wrap:wrap;gap:8px;}
.urg label{cursor:pointer;}
.urg input{position:absolute;opacity:0;width:0;height:0;}
.urg span{display:inline-block;padding:8px 14px;border-radius:var(--radius-pill);border:1px solid var(--border-strong);font-size:14px;font-weight:500;color:var(--text-muted);background:var(--surface);}
.urg input:checked+span{background:var(--primary);border-color:var(--primary);color:var(--on-primary);}
.urg input:focus-visible+span{outline:2px solid var(--primary);outline-offset:2px;}
.post-preview{white-space:pre-wrap;font-family:var(--font-sans);font-size:14px;line-height:1.5;background:var(--sunken);border:1px solid var(--border);border-radius:var(--radius-card);padding:14px 16px;margin:0;color:var(--text);min-height:140px;}
.post-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;align-items:center;}
.privacy-note{display:flex;gap:8px;align-items:center;font-size:12px;color:var(--text-muted);margin-top:10px;}
@media (max-width:600px){.spare-grid{grid-template-columns:1fr;}}
"""

URGENCIES = ("stopped", "week", "month")

SPARE_JS = """
(function(){
  var L = window.SPARE_LABELS;
  var f = document.getElementById('spare-form');
  var out = document.getElementById('spare-post');
  function val(n){ var el = f.elements[n]; return el ? (el.value || '').trim() : ''; }
  function build(){
    var urg = (f.querySelector('input[name=urgency]:checked') || {}).value || '';
    var dev = [val('device_type'), [val('brand'), val('model')].filter(Boolean).join(' ')].filter(Boolean).join(' · ');
    var lines = [L.head];
    if (dev) lines.push(L.device + ': ' + dev + (val('year') ? ' (' + val('year') + ')' : ''));
    lines.push(L.part + ': ' + (val('part') || '…'));
    if (val('markings')) lines.push(L.markings + ': ' + val('markings'));
    lines.push(L.qty + ': ' + (val('qty') || '1'));
    var where = [val('city'), val('country')].filter(Boolean).join(', ');
    if (where) lines.push(L.where + ': ' + where);
    if (urg) lines.push(L.urgency + ': ' + L['u_' + urg]);
    lines.push('');
    lines.push(L.foot);
    out.textContent = lines.join('\\n');
    document.getElementById('spare-wa').href = 'https://wa.me/?text=' + encodeURIComponent(out.textContent);
  }
  f.addEventListener('input', build);
  f.addEventListener('change', build);
  document.getElementById('spare-copy').addEventListener('click', function(){
    var btn = this, text = out.textContent;
    function done(){ btn.textContent = L.copied; setTimeout(function(){ btn.textContent = L.copy; }, 1800); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function(){ fallback(); });
    } else { fallback(); }
    function fallback(){
      var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta);
      ta.select(); try { document.execCommand('copy'); done(); } catch (e) {} ta.remove();
    }
  });
  build();
})();
"""


def _js_json(value) -> str:
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


@rt("/device/{device_id}/spare-part")
async def get(req, device_id: str, part: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    # An engineer answering a request may not be one of the clinic's own:
    # the public device data (type, brand, model, clinic region) is enough.
    try:
        data = await devices_api.get_device(token, device_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        data = None
    except Exception:
        data = None
    if data is None:
        try:
            data = await devices_api.get_device_public(device_id)
        except Exception:
            return RedirectResponse(f"/d/{device_id}", status_code=302)

    d = data.get("device", {})
    cat = d.get("category") or {}
    clinic = d.get("healthsite") or d.get("organization") or {}
    device_type = category_label(cat, lang) if cat else ""

    labels = {k: _(f"spare.{k}") for k in (
        "head", "device", "part", "markings", "qty", "where", "urgency", "foot", "copy", "copied",
        "u_stopped", "u_week", "u_month")}

    def field(name, label, value="", full=False, **kw):
        return Div(Label(label, fr=f"sp-{name}"),
                   Input(name=name, id=f"sp-{name}", value=value or "", cls="input", **kw),
                   cls="field" + (" full" if full else ""))

    form = Form(
        Div(
            field("device_type", _("spare.f_type"), device_type),
            field("year", _("spare.f_year"), str(d.get("manufacture_year") or ""), inputmode="numeric"),
            field("brand", _("spare.f_brand"), d.get("manufacturer")),
            field("model", _("spare.f_model"), d.get("model")),
            field("part", _("spare.f_part"), part, full=True, required=True, placeholder=_("spare.f_part_ph")),
            field("markings", _("spare.f_markings"), "", full=True, placeholder=_("spare.f_markings_ph")),
            field("qty", _("spare.f_qty"), "1", type="number", min="1", inputmode="numeric"),
            Div(cls="field"),
            field("city", _("spare.f_city"), clinic.get("region") or ""),
            field("country", _("spare.f_country"), clinic.get("country") or ""),
            Div(Label(_("spare.f_urgency")),
                Div(*[Label(Input(type="radio", name="urgency", value=u, checked=(u == "week")),
                            Span(_(f"spare.u_{u}"))) for u in URGENCIES], cls="urg"),
                cls="field full"),
            cls="spare-grid",
        ),
        id="spare-form", onsubmit="return false;",
    )

    content = Div(
        Style(SPARE_CSS),
        A(_("spare.back"), href=f"/device/{device_id}",
          style="font-size:14px;color:var(--text-muted);text-decoration:none;display:inline-block;margin-bottom:12px;"),
        page_head(_("spare.title"), _("spare.intro"), "wrench", "eng"),
        Div(form, cls="card", style="margin-bottom:16px;"),
        Div(
            H3(_("spare.preview"), cls="card-title"),
            Pre(id="spare-post", cls="post-preview", aria_live="polite"),
            Div(Button(_("spare.copy"), type="button", id="spare-copy", cls="btn btn-primary"),
                A(_("spare.whatsapp"), id="spare-wa", href="https://wa.me/", target="_blank", rel="noopener",
                  cls="btn btn-secondary"),
                Span(_("spare.discord_hint"), cls="muted"),
                cls="post-actions"),
            Div("🔒", Span(_("spare.privacy")), cls="privacy-note"),
            cls="card",
        ),
        Script(f"window.SPARE_LABELS = {_js_json(labels)};"),
        Script(SPARE_JS),
        cls="spare",
    )
    return page_shell(content, current="/devices", title=_("spare.title"), lang=lang)
