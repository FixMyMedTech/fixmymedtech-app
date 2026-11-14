# features/calls/pages.py — "Call an engineer" (wave 4), both phones.
#
# Clinic:   /d/{device_id}/call   what is happening + urgency → starts the call
#           /calls/{fault_id}     the ride: who was told, offers, agreement,
#                                 then the repair steps and the sign-off
# Engineer: /requests             requests near you + your offers
#           /requests/{fault_id}  send a visit offer, answer a counter-offer
#
# The steps from diagnosis on are the existing fault workflow
# (/device/{id}/fault/{fault_id}); these pages link to it.

import json
from datetime import datetime, timedelta, timezone

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.calls.api as calls_api
import features.faults.api as faults_api
import features.auth.api as auth_api
from components import page_shell, status_badge, alert, fmt_date
from i18n import t as make_t

rt = APIRouter()

STEPS = ("call", "match", "offer", "agree", "diagnose", "repair", "signoff")

CALL_CSS = """
.ride{max-width:720px;}
.stepper{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px;margin:0 0 16px;padding:0;list-style:none;}
.stepper li{display:flex;flex-direction:column;align-items:center;gap:4px;text-align:center;font-size:11px;font-weight:600;color:var(--text-muted);line-height:1.2;}
.stepper li i{font-style:normal;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--sunken);border:1px solid var(--border);font-size:12px;}
.stepper li.done i{background:var(--ok-tint);color:var(--ok);border-color:transparent;}
.stepper li.on{color:var(--text);}
.stepper li.on i{background:var(--primary);color:var(--on-primary);border-color:transparent;transform:scale(1.12);}
.ride-dev{display:flex;gap:12px;align-items:flex-start;justify-content:space-between;margin-bottom:12px;}
.ride-dev h1{font-size:20px;margin:2px 0;}
.radar{position:relative;width:132px;height:132px;margin:8px auto 12px;border-radius:50%;
  background:radial-gradient(circle,var(--primary-tint) 0 30%,transparent 31%),radial-gradient(circle,transparent 0 58%,var(--primary-tint) 59% 61%,transparent 62%);
  border:2px solid var(--primary-tint);}
.radar::after{content:"";position:absolute;inset:-2px;border-radius:50%;border:2px solid var(--primary);opacity:.6;animation:ping 2s ease-out infinite;}
.radar b{position:absolute;left:50%;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;background:var(--primary);}
@keyframes ping{from{transform:scale(.4);opacity:.8}to{transform:scale(1.15);opacity:0}}
@media (prefers-reduced-motion:reduce){.radar::after{animation:none}}
.center{text-align:center;}
.muted{color:var(--text-muted);font-size:14px;}
.offer{border:1px solid var(--border);border-radius:var(--radius-card);padding:14px;margin-top:10px;background:var(--surface);}
.offer-top{display:flex;align-items:center;gap:12px;}
.av{width:40px;height:40px;border-radius:50%;flex-shrink:0;display:grid;place-items:center;font-weight:700;font-size:14px;background:var(--primary-tint);color:var(--primary);}
.offer .who{flex:1;min-width:0;}
.offer .who b{display:block;color:var(--text);}
.price{font-size:20px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums;white-space:nowrap;}
.price small{font-size:12px;font-weight:500;color:var(--text-muted);margin-left:2px;}
.offer-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;align-items:center;}
.offer-actions form{display:flex;gap:8px;align-items:center;margin:0;}
.offer-actions input{max-width:130px;}
.bubble{display:inline-block;padding:8px 12px;border-radius:14px 14px 14px 4px;background:var(--sunken);font-size:14px;margin-top:8px;color:var(--text);}
.bubble.me{border-radius:14px 14px 4px 14px;background:var(--primary-tint);}
.agreed{background:var(--ok-tint);color:var(--ok);padding:12px 14px;border-radius:var(--radius-control);font-weight:700;margin:8px 0;}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 4px;}
.pills label{cursor:pointer;}
.pills input{position:absolute;opacity:0;width:0;height:0;}
.pills span{display:inline-block;padding:8px 14px;border-radius:var(--radius-pill);border:1px solid var(--border-strong);font-size:14px;font-weight:500;color:var(--text-muted);background:var(--surface);}
.pills input:checked+span{background:var(--primary);border-color:var(--primary);color:var(--on-primary);}
.pills input:focus-visible+span{outline:2px solid var(--primary);outline-offset:2px;}
.stars{display:flex;flex-direction:row-reverse;justify-content:flex-end;gap:4px;}
.stars input{position:absolute;opacity:0;width:0;height:0;}
.stars label{font-size:30px;line-height:1;color:var(--border-strong);cursor:pointer;}
.stars input:checked~label,.stars label:hover,.stars label:hover~label{color:var(--warn);}
.stars input:focus-visible+label{outline:2px solid var(--primary);border-radius:4px;}
.req{display:flex;gap:12px;align-items:center;padding:12px 14px;border:1px solid var(--border);border-left:4px solid var(--warn);border-radius:var(--radius-control);margin-bottom:8px;background:var(--surface);text-decoration:none;color:var(--text);}
.req.is-danger{border-left-color:var(--danger);}
.req.is-ok{border-left-color:var(--ok);}
.req:hover{border-color:var(--primary);}
.req .grow{flex:1;min-width:0;}
.req b{display:block;}
.field{margin-bottom:12px;}
.field label.lbl{display:block;font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:4px;}
@media (max-width:600px){.stepper li span{display:none;}.stepper li.on span{display:block;}}
"""

# Times are stored in UTC; this shows them in the viewer's own time zone.
LOCAL_TIME_JS = """
document.querySelectorAll('time.lt').forEach(function (t) {
  var d = new Date(t.getAttribute('datetime'));
  if (!isNaN(d)) t.textContent = d.toLocaleString(document.documentElement.lang || undefined,
    {weekday:'short', day:'numeric', month:'short', hour:'2-digit', minute:'2-digit'});
});
var tz = document.querySelectorAll('input[name=tz_offset]');
tz.forEach(function (i) { i.value = new Date().getTimezoneOffset(); });
"""


def _lt(iso) -> Time:
    s = str(iso or "")
    return Time(s[:16].replace("T", " "), datetime=s, cls="lt")


def _initials(p: dict) -> str:
    name = (p or {}).get("full_name") or (p or {}).get("username") or "?"
    parts = [x for x in name.replace(".", " ").split() if x]
    return "".join(x[0] for x in parts[:2]).upper() or "?"


def _name(p: dict) -> str:
    return (p or {}).get("full_name") or (p or {}).get("username") or ""


def _detail(e) -> str:
    try:
        return e.response.json().get("detail", "") or ""
    except Exception:
        return ""


def _phase(call: dict) -> int:
    """Index in STEPS of the step the request is at."""
    f = call.get("fault", {})
    status, cs = f.get("status"), f.get("call_status")
    if call.get("rating"):
        return 7
    if status == "resolved":
        return 6
    if status in ("approved", "in_progress"):
        return 5
    if status in ("assigned", "diagnosed"):
        return 4 if cs == "agreed" or status == "diagnosed" else 3
    if cs == "searching":
        return 2 if call.get("offers") else 1
    return 0


def _stepper(_, at: int):
    items = []
    for i, key in enumerate(STEPS):
        cls = "done" if i < at else ("on" if i == at else "")
        items.append(Li(I("✓" if i < at else str(i + 1)), Span(_(f"call.step_{key}")), cls=cls))
    return Ol(*items, cls="stepper", aria_label=_("call.steps_label"))


def _device_head(_, call: dict, lang: str):
    d = call.get("device", {})
    f = call.get("fault", {})
    urg = f.get("urgency")
    return Div(
        Div(Div(_("call.eyebrow"), cls="eyebrow"),
            H1(d.get("name", "")),
            P(" · ".join(x for x in (d.get("location"), _(f"call.urgency_{urg}") if urg else "") if x), cls="muted"),
            P(f.get("description", ""), style="margin:6px 0 0;color:var(--text);")),
        status_badge(f.get("status", "open"), "fault", lang=lang),
        cls="ride-dev",
    )


def _shell(content, title, lang, current="/faults"):
    return page_shell(Div(Style(CALL_CSS), content, Script(LOCAL_TIME_JS), cls="ride"),
                      current=current, title=title, lang=lang)


def _arrival_iso(value: str, tz_offset: str) -> str | None:
    """<input type=datetime-local> is the browser's local time; the hidden
    tz_offset (minutes, as JS getTimezoneOffset) turns it into UTC."""
    try:
        local = datetime.fromisoformat((value or "").strip())
    except ValueError:
        return None
    try:
        offset = int(tz_offset)
    except (TypeError, ValueError):
        offset = 0
    return (local + timedelta(minutes=offset)).replace(tzinfo=timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════
# CLINIC: CALL
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/call")
async def get(req, device_id: str, error: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/call", status_code=302)
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    form = Form(
        Div(Label(_("call.what_label"), cls="lbl", fr="description"),
            Textarea(name="description", id="description", rows="3", cls="input", required=True,
                     placeholder=_("call.what_placeholder")), cls="field"),
        Div(Span(_("call.urgency_label"), cls="lbl", style="font-size:12px;font-weight:600;color:var(--text-muted);"),
            Div(Label(Input(type="radio", name="urgency", value="now", checked=True), Span(_("call.urgency_now"))),
                Label(Input(type="radio", name="urgency", value="this_week"), Span(_("call.urgency_this_week"))),
                cls="pills", role="radiogroup"), cls="field"),
        Div(Label(_("call.photo_label"), cls="lbl", fr="photo"),
            Input(type="file", name="photo", id="photo", accept="image/*", capture="environment", cls="input"),
            cls="field"),
        Button(_("call.call_btn"), type="submit", cls="btn btn-primary", style="width:100%;font-size:16px;padding:12px;"),
        P(_("call.call_note"), cls="muted", style="margin-top:8px;font-size:12px;"),
        method="post", action=f"/d/{device_id}/call", enctype="multipart/form-data",
    )
    content = Div(
        A(_("public_qr.back"), href=f"/d/{device_id}", cls="muted",
          style="text-decoration:none;display:inline-block;margin-bottom:12px;"),
        _stepper(_, 0),
        alert(_(f"call.error_{error}") if error in ("not_clinic", "failed") else _("call.error_failed"), "error") if error else "",
        Div(H2(_("call.heading"), style="margin:0 0 4px;"), P(_("call.intro"), cls="muted"), form, cls="card"),
    )
    return _shell(content, _("call.heading"), lang, current="/devices")


@rt("/d/{device_id}/call", methods=["post"])
async def post(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    description = (form.get("description") or "").strip()
    urgency = form.get("urgency") if form.get("urgency") in ("now", "this_week") else "now"
    if not description:
        return RedirectResponse(f"/d/{device_id}/call", status_code=303)
    try:
        me = await auth_api.get_me(token)
        name = me.get("full_name") or req.session.get("user_email", "")
    except Exception:
        name = req.session.get("user_email", "")
    try:
        result = await faults_api.submit_fault_public({
            "device_id": device_id, "description": description,
            "severity": "high" if urgency == "now" else "medium", "reporter_name": name,
        }, token)
        fault_id = str(result.get("id"))
    except Exception:
        return RedirectResponse(f"/d/{device_id}/call?error=failed", status_code=303)
    photo = form.get("photo")
    if photo is not None and getattr(photo, "filename", ""):
        try:
            data = await photo.read()
            if data:
                await faults_api.upload_fault_photo(token, fault_id, photo.filename, data, photo.content_type)
        except Exception:
            pass
    try:
        await calls_api.start(token, fault_id, urgency)
    except httpx.HTTPStatusError as e:
        # Not one of the clinic's people: the fault is still reported, the
        # clinic's engineers see it in their faults list.
        if e.response.status_code == 403:
            return RedirectResponse(f"/d/{device_id}/fault/{fault_id}", status_code=303)
        return RedirectResponse(f"/calls/{fault_id}?error=failed", status_code=303)
    return RedirectResponse(f"/calls/{fault_id}", status_code=303)


@rt("/calls/{fault_id}/start", methods=["post"])
async def post_start(req, fault_id: str, urgency: str = "now"):
    """Call an engineer on a fault that was already reported."""
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await calls_api.start(token, fault_id, urgency if urgency in ("now", "this_week") else "now")
    except Exception:
        return RedirectResponse(f"/calls/{fault_id}?error=failed", status_code=303)
    return RedirectResponse(f"/calls/{fault_id}", status_code=303)


# ══════════════════════════════════════════════════════════════
# CLINIC: THE RIDE
# ══════════════════════════════════════════════════════════════

def _offer_card(_, o: dict, currency: str, decider: bool, can_counter: bool, fault_id: str = ""):
    eng = o.get("engineer") or {}
    stars = ""
    if o.get("rating_count"):
        stars = f"★ {o['rating_avg']} ({o['rating_count']})"
    status = o.get("status")
    body = [
        Div(Div(_initials(eng), cls="av", aria_hidden="true"),
            Div(B(_name(eng)), Div(" · ".join(x for x in (stars or _("call.new_engineer"), eng.get("city")) if x), cls="muted"), cls="who"),
            Div(o.get("fee_label", ""), Small(currency), cls="price"),
            cls="offer-top"),
        Div(_("call.can_be_there"), " ", _lt(o.get("arrival_at")), cls="muted", style="margin-top:6px;"),
        Div(o["note"], cls="bubble") if o.get("note") else "",
    ]
    if o.get("counter_label"):
        body.append(Div(Div(_("call.you_asked").format(fee=f"{o['counter_label']} {currency}"), cls="bubble me")))
    actions = []
    if decider and status == "pending":
        actions.append(Form(Input(type="hidden", name="fault", value=fault_id),
                            Button(_("call.accept_btn"), type="submit", cls="btn btn-primary btn-sm"),
                            method="post", action=f"/calls/offers/{o['id']}/accept"))
        if can_counter and not o.get("countered_at"):
            actions.append(Form(
                Input(type="hidden", name="fault", value=fault_id),
                Input(type="number", name="fee", min="0", step="any", required=True, cls="input",
                      placeholder=_("call.counter_placeholder"), aria_label=_("call.counter_placeholder")),
                Button(_("call.counter_btn"), type="submit", cls="btn btn-secondary btn-sm"),
                method="post", action=f"/calls/offers/{o['id']}/counter"))
    elif status == "countered":
        actions.append(Span(_("call.waiting_engineer"), cls="badge badge-warn"))
    elif status in ("declined", "withdrawn", "lapsed"):
        actions.append(Span(_(f"call.offer_{status}"), cls="badge badge-neutral"))
    elif status == "accepted":
        actions.append(Span(_("call.offer_accepted"), cls="badge badge-ok"))
    if actions:
        body.append(Div(*actions, cls="offer-actions"))
    return Div(*body, cls="offer")


def _sign_off_form(_, fault_id: str):
    stars = []
    for n in range(5, 0, -1):
        stars += [Input(type="radio", name="rating", value=str(n), id=f"star{n}"),
                  Label("★", fr=f"star{n}", title=_("call.stars").format(n=n))]
    return Div(
        H3(_("call.signoff_heading"), cls="card-title"),
        P(_("call.signoff_body"), cls="muted"),
        Form(
            Div(Span(_("call.rate_label"), style="font-size:12px;font-weight:600;color:var(--text-muted);"),
                Div(*stars, cls="stars", role="radiogroup", aria_label=_("call.rate_label")), cls="field"),
            Div(Label(_("call.comment_label"), cls="lbl", fr="comment"),
                Textarea(name="comment", id="comment", rows="2", cls="input"), cls="field"),
            Div(Button(_("call.works_btn"), type="submit", name="works", value="1", cls="btn btn-primary"),
                Button(_("call.not_works_btn"), type="submit", name="works", value="0", cls="btn btn-secondary",
                       formnovalidate=True),
                style="display:flex;gap:8px;flex-wrap:wrap;"),
            method="post", action=f"/calls/{fault_id}/signoff",
        ),
        cls="card", style="margin-top:16px;",
    )


@rt("/calls/{fault_id}")
async def get_call(req, fault_id: str, error: str = "", msg: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        call = await calls_api.get_call(token, fault_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse("/faults", status_code=302)
    viewer = call.get("viewer", {})
    if not viewer.get("is_decider"):
        return RedirectResponse(f"/requests/{fault_id}", status_code=302)
    f = call.get("fault", {})
    d = call.get("device", {})
    cur = call.get("currency", "")
    at = _phase(call)
    offers = call.get("offers", [])
    told = call.get("told", {})
    fault_href = f"/device/{d.get('id')}/fault/{fault_id}"
    cs = f.get("call_status")

    if cs == "searching":
        names = [n for n in told.get("names", []) if n]
        if names:
            who = _("call.told_names").format(names=", ".join(names[:3]), n=max(0, told.get("total", 0) - 3)) \
                if len(names) > 3 else _("call.told_list").format(names=", ".join(names))
        else:
            who = _("call.told_nobody")
        stage = Div(
            Div(Div(B(), cls="radar", aria_hidden="true"),
                H3(_("call.looking") if not offers else _("call.offers_in").format(n=len([o for o in offers if o.get('status') in ('pending', 'countered')]))),
                P(who, cls="muted"),
                P(_("call.widened") if f.get("call_widened_at") else _("call.will_widen"), cls="muted", style="font-size:12px;"),
                cls="center"),
            *[_offer_card(_, o, cur, True, viewer.get("can_counter", True), fault_id) for o in offers],
            Form(Button(_("call.cancel_btn"), type="submit", cls="btn btn-secondary btn-sm"),
                 method="post", action=f"/calls/{fault_id}/cancel", style="margin-top:14px;"),
            cls="card",
        )
    elif cs in ("agreed", "closed") or f.get("assigned_to"):
        acc = next((o for o in offers if o.get("status") == "accepted"), None)
        eng = call.get("assignee") or (acc or {}).get("engineer") or {}
        lines = []
        if acc:
            lines.append(Div(_("call.agreed_line").format(fee=f"{acc.get('agreed_label')} {cur}", name=_name(eng)),
                             " · ", _lt(acc.get("arrival_at")), cls="agreed"))
        elif cs == "closed" and not f.get("assigned_to"):
            lines.append(P(_("call.cancelled"), cls="muted"))
        nxt = {
            3: _("call.next_diagnose"), 4: _("call.next_diagnose"), 5: _("call.next_repair"),
            6: _("call.next_signoff"), 7: _("call.done"),
        }.get(at, "")
        stage = Div(*lines, P(nxt), A(_("call.open_fault"), href=fault_href, cls="btn btn-secondary btn-sm"),
                    cls="card")
    else:
        stage = Div(H3(_("call.not_called")), P(_("call.not_called_body"), cls="muted"),
                    Form(Input(type="hidden", name="urgency", value="now"),
                         Button(_("call.call_btn"), type="submit", cls="btn btn-primary"),
                         method="post", action=f"/calls/{fault_id}/start"),
                    cls="card")

    rating = call.get("rating")
    tail = ""
    if f.get("status") == "resolved" and not rating:
        tail = _sign_off_form(_, fault_id)
    elif rating:
        tail = Div(H3(_("call.signed_off")), P("★" * int(rating.get("rating", 0)), style="color:var(--warn);font-size:22px;margin:0;"),
                   P(rating.get("comment") or "", cls="muted"), cls="card", style="margin-top:16px;")

    content = Div(
        A(_("call.back_device"), href=f"/device/{d.get('id')}", cls="muted",
          style="text-decoration:none;display:inline-block;margin-bottom:12px;"),
        _stepper(_, at),
        alert(_("call.error_failed") + (f" ({error})" if error not in ("1", "failed") else ""), "error") if error else "",
        alert(_(f"call.msg_{msg}"), "success") if msg in ("accepted", "countered", "signed", "reopened") else "",
        Div(_device_head(_, call, lang), cls="card", style="margin-bottom:16px;"),
        stage,
        tail,
    )
    return _shell(content, d.get("name", _("call.heading")), lang)


async def _act(req, call, ok_url, err_url):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await call(token)
    except httpx.HTTPStatusError as e:
        return RedirectResponse(f"{err_url}?error={_detail(e)[:80] or 'failed'}", status_code=303)
    except Exception:
        return RedirectResponse(f"{err_url}?error=failed", status_code=303)
    return RedirectResponse(ok_url, status_code=303)


@rt("/calls/{fault_id}/cancel", methods=["post"])
async def post_cancel(req, fault_id: str):
    return await _act(req, lambda t: calls_api.cancel(t, fault_id), f"/calls/{fault_id}", f"/calls/{fault_id}")


@rt("/calls/offers/{offer_id}/accept", methods=["post"])
async def post_accept(req, offer_id: str, fault: str = ""):
    fault_id = fault or await _fault_of(req, offer_id)
    return await _act(req, lambda t: calls_api.accept(t, offer_id),
                      f"/calls/{fault_id}?msg=accepted", f"/calls/{fault_id}")


@rt("/calls/offers/{offer_id}/counter", methods=["post"])
async def post_counter(req, offer_id: str, fee: str = "0", fault: str = ""):
    fault_id = fault or await _fault_of(req, offer_id)
    try:
        amount = float(fee)
    except ValueError:
        return RedirectResponse(f"/calls/{fault_id}?error=failed", status_code=303)
    return await _act(req, lambda t: calls_api.counter(t, offer_id, amount),
                      f"/calls/{fault_id}?msg=countered", f"/calls/{fault_id}")


async def _fault_of(req, offer_id: str) -> str:
    """Fallback when a form lacks its hidden fault id: the referring page."""
    ref = req.headers.get("referer", "")
    for prefix in ("/calls/", "/requests/"):
        if prefix in ref:
            return ref.split(prefix, 1)[1].split("?", 1)[0].split("/", 1)[0]
    return ""


@rt("/calls/{fault_id}/signoff", methods=["post"])
async def post_signoff(req, fault_id: str):
    form = await req.form()
    works = form.get("works") == "1"
    data = {"works": works, "comment": (form.get("comment") or "").strip()}
    if works:
        try:
            data["rating"] = int(form.get("rating") or 0) or None
        except ValueError:
            data["rating"] = None
        if not data["rating"]:
            return RedirectResponse(f"/calls/{fault_id}?error=stars", status_code=303)
    return await _act(req, lambda t: calls_api.sign_off(t, fault_id, data),
                      f"/calls/{fault_id}?msg={'signed' if works else 'reopened'}", f"/calls/{fault_id}")


# ══════════════════════════════════════════════════════════════
# ENGINEER: REQUESTS NEAR YOU
# ══════════════════════════════════════════════════════════════

@rt("/requests")
async def get_requests(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        data = await calls_api.inbox(token)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        data = {}
    cur = data.get("currency", "")

    def item(r, mine=False):
        tone = "danger" if r.get("urgency") == "now" else "warn"
        sub = [r.get("location") or "", _(f"call.urgency_{r.get('urgency')}") if r.get("urgency") else ""]
        right = Span(_("call.tier_" + (r.get("tier") or "city")), cls="badge badge-neutral")
        if mine:
            st = r.get("offer_status")
            tone = "ok" if st == "accepted" else "warn"
            label = {"pending": _("call.offer_pending"), "countered": _("call.counter_waiting"),
                     "accepted": _("call.offer_accepted")}.get(st, st)
            right = Span(f"{r.get('fee_label')} {cur} · {label}",
                         cls="badge " + ("badge-ok" if st == "accepted" else "badge-warn"))
        return A(Div(B(r.get("device_name", "")), Span(" · ".join(x for x in sub if x), cls="muted"),
                     Div(r.get("description", "")[:90], cls="muted", style="font-size:12px;"), cls="grow"),
                 right, href=f"/requests/{r['fault_id']}", cls=f"req is-{tone}")

    open_ = data.get("open", [])
    mine = data.get("mine", [])
    content = Div(
        H1(_("call.requests_title")),
        P(_("call.requests_intro"), cls="muted", style="margin-bottom:16px;"),
        alert(_("call.unlock_to_offer"), "info") if data and not data.get("can_offer") else "",
        Div(H3(_("call.your_offers"), cls="card-title"), *[item(r, True) for r in mine], cls="card",
            style="margin-bottom:16px;") if mine else "",
        Div(H3(_("call.near_you"), cls="card-title"),
            *([item(r) for r in open_] or [P(_("call.nothing_new"), cls="muted")]), cls="card"),
    )
    return _shell(content, _("call.requests_title"), lang, current="/requests")


@rt("/requests/{fault_id}")
async def get_request(req, fault_id: str, error: str = "", msg: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        call = await calls_api.get_call(token, fault_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        return RedirectResponse("/requests", status_code=302)
    viewer = call.get("viewer", {})
    f = call.get("fault", {})
    d = call.get("device", {})
    cur = call.get("currency", "")
    mine = next((o for o in call.get("offers", []) if o.get("mine")), None)
    fault_href = f"/device/{d.get('id')}/fault/{fault_id}"

    if viewer.get("can_offer"):
        soon = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:00")
        stage = Div(
            H3(_("call.your_offer"), cls="card-title"),
            P(_("call.offer_explain"), cls="muted"),
            Form(
                Input(type="hidden", name="tz_offset", value="0"),
                Div(Label(_("call.fee_label").format(cur=cur), cls="lbl", fr="fee"),
                    Input(type="number", name="visit_fee", id="fee", min="0", step="any", required=True,
                          cls="input", inputmode="numeric"), cls="field"),
                Div(Label(_("call.arrival_label"), cls="lbl", fr="arrival"),
                    Input(type="datetime-local", name="arrival_at", id="arrival", value=soon, required=True,
                          cls="input"), cls="field"),
                Div(Label(_("call.note_label"), cls="lbl", fr="note"),
                    Input(type="text", name="note", id="note", maxlength="200", cls="input",
                          placeholder=_("call.note_placeholder")), cls="field"),
                Button(_("call.send_offer"), type="submit", cls="btn btn-primary", style="width:100%;"),
                method="post", action=f"/requests/{fault_id}/offer",
            ),
            Form(Button(_("call.pass_btn"), type="submit", cls="btn btn-secondary btn-sm"),
                 method="post", action=f"/requests/{fault_id}/pass", style="margin-top:10px;"),
            cls="card",
        )
    elif mine:
        st = mine.get("status")
        parts = [Div(Div(mine.get("fee_label"), Small(cur), cls="price"),
                     Div(_("call.can_be_there"), " ", _lt(mine.get("arrival_at")), cls="muted"))]
        if mine.get("note"):
            parts.append(Div(mine["note"], cls="bubble me"))
        if st == "countered":
            parts += [Div(_("call.clinic_asks").format(fee=f"{mine.get('counter_label')} {cur}"), cls="bubble"),
                      Div(Form(Input(type="hidden", name="take", value="1"),
                               Button(_("call.take_counter"), type="submit", cls="btn btn-primary btn-sm"),
                               Input(type="hidden", name="fault", value=fault_id),
                               method="post", action=f"/requests/offers/{mine['id']}/answer"),
                          Form(Input(type="hidden", name="take", value="0"),
                               Button(_("call.refuse_counter"), type="submit", cls="btn btn-secondary btn-sm"),
                               Input(type="hidden", name="fault", value=fault_id),
                               method="post", action=f"/requests/offers/{mine['id']}/answer"),
                          cls="offer-actions")]
        elif st == "pending":
            parts += [P(_("call.offer_sent"), cls="muted"),
                      Form(Input(type="hidden", name="fault", value=fault_id),
                           Button(_("call.withdraw_btn"), type="submit", cls="btn btn-secondary btn-sm"),
                           method="post", action=f"/requests/offers/{mine['id']}/withdraw")]
        elif st == "accepted":
            parts += [Div(_("call.accepted_by_clinic").format(fee=f"{mine.get('agreed_label')} {cur}"), cls="agreed"),
                      A(_("call.on_my_way"), href=fault_href, cls="btn btn-primary", style="width:100%;text-align:center;")]
        else:
            parts.append(Span(_(f"call.offer_{st}"), cls="badge badge-neutral"))
        stage = Div(H3(_("call.your_offer"), cls="card-title"), *parts, cls="card")
    elif viewer.get("passed"):
        stage = Div(P(_("call.you_passed"), cls="muted"), cls="card")
    else:
        stage = Div(P(_("call.closed_for_you"), cls="muted"), cls="card")

    content = Div(
        A(_("call.back_requests"), href="/requests", cls="muted",
          style="text-decoration:none;display:inline-block;margin-bottom:12px;"),
        _stepper(_, _phase(call) if mine and mine.get("status") == "accepted" else (2 if viewer.get("can_offer") else 3)),
        alert(_("call.error_failed") + (f" ({error})" if error not in ("1", "failed") else ""), "error") if error else "",
        alert(_(f"call.msg_{msg}"), "success") if msg in ("sent", "answered", "withdrawn") else "",
        Div(_device_head(_, call, lang), cls="card", style="margin-bottom:16px;"),
        stage,
    )
    return _shell(content, d.get("name", _("call.requests_title")), lang, current="/requests")


@rt("/requests/{fault_id}/offer", methods=["post"])
async def post_offer(req, fault_id: str):
    form = await req.form()
    arrival = _arrival_iso(form.get("arrival_at"), form.get("tz_offset"))
    try:
        fee = float(form.get("visit_fee") or "")
    except ValueError:
        fee = None
    if arrival is None or fee is None:
        return RedirectResponse(f"/requests/{fault_id}?error=failed", status_code=303)
    data = {"visit_fee": fee, "arrival_at": arrival, "note": (form.get("note") or "").strip()}
    return await _act(req, lambda t: calls_api.make_offer(t, fault_id, data),
                      f"/requests/{fault_id}?msg=sent", f"/requests/{fault_id}")


@rt("/requests/{fault_id}/pass", methods=["post"])
async def post_pass(req, fault_id: str):
    return await _act(req, lambda t: calls_api.pass_call(t, fault_id), "/requests", f"/requests/{fault_id}")


@rt("/requests/offers/{offer_id}/answer", methods=["post"])
async def post_answer(req, offer_id: str, take: str = "0", fault: str = ""):
    # Not "accept": FastHTML would fill that from the Accept header.
    fault_id = fault or await _fault_of(req, offer_id)
    return await _act(req, lambda t: calls_api.answer(t, offer_id, take == "1"),
                      f"/requests/{fault_id}?msg=answered", f"/requests/{fault_id}")


@rt("/requests/offers/{offer_id}/withdraw", methods=["post"])
async def post_withdraw(req, offer_id: str, fault: str = ""):
    fault_id = fault or await _fault_of(req, offer_id)
    return await _act(req, lambda t: calls_api.withdraw(t, offer_id),
                      f"/requests/{fault_id}?msg=withdrawn", f"/requests/{fault_id}")
