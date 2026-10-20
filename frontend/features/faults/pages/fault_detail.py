# pages/fault_detail.py — a fault's timeline and the step forms.
#
# A fault moves through five steps and a different person owns each one:
#   1. anyone reports it                       2. the maintenance-org admin assigns it
#   3. the assignee diagnoses + quotes         4. the healthsite admin approves/rejects
#   5. the assignee repairs it and prices it
# This page shows the whole timeline with the actor and date of every step, and
# renders only the form(s) the signed-in user is actually allowed to act on.

from fasthtml.common import *
from starlette.responses import RedirectResponse, Response
import httpx

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.faults.api as faults_api

from components import page_shell, status_badge, fmt_date, assignee_options
from i18n import t as make_t
rt = APIRouter()

# Codes the POST handlers hand back through ?err=, mapped to i18n keys.
_ERRORS = {
    "assign": "fault_detail.err_assign",
    "diagnosis": "fault_detail.err_diagnosis",
    "approval": "fault_detail.err_approval",
    "resolve": "fault_detail.err_resolve",
    "comment_required": "fault_detail.err_comment_required",
    "conflict": "fault_detail.err_conflict",
    "forbidden": "fault_detail.err_forbidden",
}

# Codes handed back through ?ok= when a step actually went through.
_SUCCESS = {
    "assign": "fault_detail.ok_assign",
    "start": "fault_detail.ok_start",
    "diagnosis": "fault_detail.ok_diagnosis",
    "approval": "fault_detail.ok_approval",
    "reject": "fault_detail.ok_reject",
    "resolve": "fault_detail.ok_resolve",
}


def _person(p, fallback=""):
    if isinstance(p, dict):
        return p.get("full_name") or p.get("username") or fallback
    return fallback


def _step(_, key, when, who, extra="", state="done"):
    """One timeline entry. state is done | current | pending | rejected."""
    mark = {"done": "✓", "rejected": "✕", "current": "●", "pending": "○"}[state]
    colour = {
        "done": "var(--c-green)",
        "rejected": "var(--c-red, #dc2626)",
        "current": "var(--c-primary)",
        "pending": "var(--c-text-3)",
    }[state]
    line2 = " · ".join(filter(None, [when, who]))
    return Div(
        Span(mark, style=f"color:{colour};font-size:0.95rem;width:18px;display:inline-block;flex:none;"),
        Div(
            Div(_(key), style=f"font-weight:600;font-size:0.85rem;color:{colour};"),
            Div(line2, style="font-size:0.78rem;color:var(--c-text-3);margin-top:2px;")
            if line2 else "",
            Div(extra, style="font-size:0.8rem;color:var(--c-text-2);margin-top:4px;"
                             "white-space:pre-wrap;") if extra else "",
            style="min-width:0;",
        ),
        style="display:flex;gap:10px;padding:9px 0;border-bottom:1px solid var(--c-border);",
    )


@rt("/device/{device_id}/fault/{fault_id}/photo")
async def get_fault_photo(req, device_id: str, fault_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    try:
        content, ctype = await faults_api.get_fault_photo(token, fault_id)
        return Response(content=content, media_type=ctype)
    except Exception:
        return Response(status_code=404)


@rt("/device/{device_id}/fault/{fault_id}")
async def get(req, device_id: str, fault_id: str, err: str = "", ok: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}

    try:
        fault = await faults_api.get_fault(token, fault_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        if e.response.status_code == 403:
            return page_shell(
                Div(
                    Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                    H2(_("fault_detail.denied_heading")),
                    P(_("fault_detail.denied_msg")),
                    A(_("device_detail.back"), href=f"/device/{device_id}",
                      cls="btn btn-secondary", style="margin-top:16px;"),
                    style="text-align:center;padding:60px 24px;"
                ),
                current="/faults", lang=lang, title=f"{_('title.device_detail')}"
            )
        return RedirectResponse(f"/device/{device_id}", status_code=302)
    except Exception:
        return RedirectResponse(f"/device/{device_id}", status_code=302)

    device = fault.get("device") or {}
    assigned = fault.get("assigned_to_profile") or {}
    reported_by = fault.get("reported_by_profile") or {}
    status = fault.get("status", "open")
    actions = auth_helper.fault_actions(me, fault)

    rows = [
        (_("fault_detail.status"),      status_badge(status, "fault", lang=lang)),
        (_("fault_detail.severity"),    status_badge(fault.get("severity", "medium"), "severity", lang=lang)),
        (_("fault_detail.reported_at"), fmt_date(fault.get("reported_at", ""))),
        (_("fault_detail.reported_by"), _person(reported_by, fault.get("reporter_name", "")) or _("common.fallback")),
        (_("fault_detail.assigned_to"), _person(assigned) or _("fault_list.unassigned")),
    ]
    if fault.get("quote_amount") is not None:
        rows.append((_("fault_detail.quote_amount"), f"{fault['quote_amount']:.2f}"))
    if fault.get("final_price") is not None:
        rows.append((_("fault_detail.final_price"), f"{fault['final_price']:.2f}"))

    info_card = Div(
        H3(_("fault_detail.info"), style="margin-bottom:12px;"),
        Dl(*[Div(Dt(k, style="color:var(--c-text-3);font-weight:500;"), Dd(v),
                 style="display:flex;justify-content:space-between;padding:8px 0;"
                       "border-bottom:1px solid var(--c-border);font-size:0.875rem;gap:16px;")
             for k, v in rows]),
        cls="card",
    )

    description_card = Div(
        H3(_("fault_detail.description"), style="margin-bottom:12px;"),
        P(fault.get("description", ""), style="font-size:0.9rem;white-space:pre-wrap;"),
        cls="card",
    )

    photo_card = Div(
        H3(_("fault_detail.photo"), style="margin-bottom:12px;"),
        Img(src=f"/device/{device_id}/fault/{fault_id}/photo?v={fault.get('photo_key') or 'x'}",
            alt=_("fault_detail.photo"),
            style="width:100%;height:auto;border-radius:var(--r-md);"),
        cls="card",
    ) if fault.get("photo_key") else ""

    resolution_card = Div(
        H3(_("fault_detail.resolution"), style="margin-bottom:12px;"),
        P(fault.get("resolution_notes", _("fault_detail.no_resolution")),
          style="font-size:0.9rem;white-space:pre-wrap;color:var(--c-text-2);"),
        cls="card",
    ) if fault.get("resolution_notes") else ""

    # ── timeline ───────────────────────────────────────────────────────────
    approval_state = "pending"
    if fault.get("approval_status") == "approved":
        approval_state = "done"
    elif fault.get("approval_status") == "rejected":
        approval_state = "rejected"
    elif status == "diagnosed":
        approval_state = "current"

    quote_line = ""
    if fault.get("quote_amount") is not None:
        quote_line = _("fault_detail.quote_amount") + f" {fault['quote_amount']:.2f}"
        if fault.get("quote_notes"):
            quote_line += "\n" + fault["quote_notes"]

    approval_extra = _person(fault.get("approved_by_profile"))
    if fault.get("approval_comment"):
        approval_extra = (approval_extra + "\n" if approval_extra else "") + fault["approval_comment"]

    price_line = ""
    if fault.get("final_price") is not None:
        price_line = _("fault_detail.final_price") + f" {fault['final_price']:.2f}"

    assignee_who = _person(assigned)
    timeline = Div(
        H3(_("fault_detail.timeline"), style="margin-bottom:12px;"),
        _step(_, "fault_detail.step_reported",
              fmt_date(fault.get("reported_at")),
              _person(reported_by, fault.get("reporter_name", "")),
              state="done"),
        _step(_, "fault_detail.step_assigned",
              fmt_date(fault.get("assigned_at")),
              _person(fault.get("assigned_by_profile")) + (f" → {assignee_who}" if assignee_who else ""),
              state="done" if fault.get("assigned_at") else
                    ("current" if status in ("open", "assigned") else "pending")),
        _step(_, "fault_detail.step_diagnosis",
              fmt_date(fault.get("diagnosed_at")),
              _person(fault.get("diagnosed_by_profile")),
              quote_line,
              state="done" if fault.get("diagnosed_at") else
                    ("current" if status == "assigned" else "pending")),
        _step(_, "fault_detail.step_approval" if fault.get("approval_status") != "rejected"
              else "fault_detail.step_rejected",
              fmt_date(fault.get("approved_at")),
              approval_extra,
              state=approval_state),
        _step(_, "fault_detail.step_resolved",
              fmt_date(fault.get("resolved_at")),
              _person(fault.get("resolved_by_profile")),
              price_line,
              state="done" if fault.get("resolved_at") else
                    ("current" if status in ("approved", "in_progress") else "pending")),
        cls="card",
    )

    # ── step forms (only the ones this user may act on) ────────────────────
    err_box = Div(_(_ERRORS.get(err, "")), cls="alert alert-error",
                  style="margin-bottom:14px;") if err in _ERRORS else ""
    ok_box = Div(_(_SUCCESS.get(ok, "")), cls="alert alert-success",
                 style="margin-bottom:14px;") if ok in _SUCCESS else ""

    action_cards = []
    return_url = f"/device/{device_id}/fault/{fault_id}"

    if "assign" in actions:
        try:
            assignees = await faults_api.get_fault_assignees(token, device_id)
        except Exception:
            assignees = []
        action_cards.append(Div(
            H3(_("fault_detail.assign_heading"), style="margin-bottom:12px;"),
            P(_("fault_detail.assign_msg"), style="font-size:0.85rem;color:var(--c-text-3);margin:0 0 12px;"),
            Form(
                Label(_("fault_list.assign_to"), cls="label", for_="assigned_to"),
                Select(*assignee_options(assignees, str(fault.get("assigned_to") or ""), lang),
                       name="assigned_to", cls="input"),
                Button(_("fault_list.assign"), type="submit", cls="btn btn-primary",
                       style="margin-top:12px;"),
                method="post", action=f"{return_url}/assign",
            ),
            cls="card",
        ))

    if "start" in actions:
        action_cards.append(Div(
            H3(_("fault_detail.start_heading"), style="margin-bottom:12px;"),
            P(_("fault_detail.start_msg"), style="font-size:0.85rem;color:var(--c-text-3);margin:0 0 12px;"),
            Form(Button(_("fault_detail.start_btn"), type="submit", cls="btn btn-secondary"),
                 method="post", action=f"{return_url}/start"),
            cls="card",
        ))

    if "diagnosis" in actions:
        action_cards.append(Div(
            H3(_("fault_detail.diagnosis_heading"), style="margin-bottom:12px;"),
            Form(
                Div(Label(_("fault_detail.diagnosis_label"), cls="label", for_="diagnosis"),
                    Textarea(fault.get("diagnosis") or "", name="diagnosis", rows="4", cls="input",
                             placeholder=_("fault_detail.diagnosis_placeholder")),
                    cls="form-group"),
                Div(Label(_("fault_detail.quote_amount_label"), cls="label", for_="quote_amount"),
                    Input(type="number", name="quote_amount", cls="input", step="0.01", min="0",
                          value=fault.get("quote_amount") if fault.get("quote_amount") is not None else ""),
                    cls="form-group"),
                Div(Label(_("fault_detail.quote_notes_label"), cls="label", for_="quote_notes"),
                    Textarea(fault.get("quote_notes") or "", name="quote_notes", rows="2", cls="input"),
                    cls="form-group"),
                Button(_("fault_detail.diagnosis_btn"), type="submit", cls="btn btn-primary"),
                method="post", action=f"{return_url}/diagnosis",
            ),
            cls="card",
        ))

    if "approval" in actions:
        submitted = ""
        if fault.get("diagnosis"):
            submitted += fault["diagnosis"]
        if fault.get("quote_amount") is not None:
            submitted += ("\n" if submitted else "") + \
                f"{_('fault_detail.quote_amount')} {fault['quote_amount']:.2f}"
        if fault.get("quote_notes"):
            submitted += ("\n" if submitted else "") + fault["quote_notes"]
        action_cards.append(Div(
            H3(_("fault_detail.approval_heading"), style="margin-bottom:12px;"),
            P(_("fault_detail.approval_msg"), style="font-size:0.85rem;color:var(--c-text-3);margin:0 0 12px;"),
            P(submitted or _("fault_detail.no_diagnosis"),
              style="font-size:0.875rem;white-space:pre-wrap;background:var(--c-bg-2);"
                    "padding:12px;border-radius:var(--r-md);margin:0 0 14px;"),
            Form(
                Div(Label(_("fault_detail.approval_comment"), cls="label", for_="comment"),
                    Textarea(name="comment", rows="2", cls="input",
                             placeholder=_("fault_detail.approval_comment_hint")),
                    cls="form-group"),
                Div(
                    Button(_("fault_detail.approve_btn"), name="approved", value="yes",
                           type="submit", cls="btn btn-primary"),
                    Button(_("fault_detail.reject_btn"), name="approved", value="no",
                           type="submit", cls="btn btn-danger"),
                    style="display:flex;gap:8px;",
                ),
                method="post", action=f"{return_url}/approval",
            ),
            cls="card",
        ))

    if "resolve" in actions:
        action_cards.append(Div(
            H3(_("fault_detail.resolve_heading"), style="margin-bottom:12px;"),
            Form(
                Div(Label(_("fault_detail.resolution_label"), cls="label", for_="resolution_notes"),
                    Textarea(fault.get("resolution_notes") or "", name="resolution_notes",
                             rows="4", cls="input",
                             placeholder=_("fault_detail.resolution_placeholder")),
                    cls="form-group"),
                Div(Label(_("fault_detail.final_price_label"), cls="label", for_="final_price"),
                    Input(type="number", name="final_price", cls="input", step="0.01", min="0",
                          value=fault.get("final_price") if fault.get("final_price") is not None else ""),
                    cls="form-group"),
                Button(_("fault_detail.resolve_btn"), type="submit", cls="btn btn-primary"),
                method="post", action=f"{return_url}/resolve",
            ),
            cls="card",
        ))

    details_col = Div(
        info_card,
        description_card,
        resolution_card,
        style="display:flex;flex-direction:column;gap:16px;min-width:0;",
    )

    side_col = Div(
        ok_box,
        err_box,
        timeline,
        *action_cards,
        style="display:flex;flex-direction:column;gap:16px;min-width:0;",
    )

    _crumb = ("font-size:0.875rem;color:var(--c-text-3);text-decoration:none;")
    content = Div(
        Div(
            A(_("nav.faults"), href="/faults", style=_crumb),
            Span(" / ", style=_crumb + "cursor:default;"),
            A(device.get("name", "") or _("common.fallback"),
              href=f"/device/{device_id}", style=_crumb),
            style="margin-bottom:14px;",
        ),
        Div(
            Div(
                H1(_("fault_detail.heading"), style="margin-bottom:4px;"),
                P(_("fault_detail.desc"), style="color:var(--c-text-3);"),
            ),
            cls="page-header", style="margin-bottom:14px;"
        ),
        Div(details_col, side_col, cls="fault-detail-grid"),
        Style("""
        .fault-detail-grid { display:grid; grid-template-columns:1fr; gap:16px; }
        @media (min-width:900px) { .fault-detail-grid { grid-template-columns:1fr 380px; align-items:start; } }
        """),
    )

    return page_shell(content, current="/faults", lang=lang, title=f"{_('title.device_detail')}")


# ── step POSTs ───────────────────────────────────────────────────────────────

def _detail(e) -> str:
    """The API's `detail` string out of an HTTPStatusError, if any."""
    try:
        return str(e.response.json().get("detail") or "")
    except Exception:
        return ""


async def _act(token, fault_id, device_id, call, code, ok_code=None):
    """Run a step, then come back to the detail page. A failure is reported
    through ?err= and a success through ?ok= — never both, and never an error
    for a step that actually went through."""
    try:
        await call()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 401:
            return RedirectResponse("/login?expired=1", status_code=302)
        detail = _detail(e).lower()
        if status == 409:
            code = "conflict"
        elif status == 403:
            code = "forbidden"
        elif status == 400 and "comment is required" in detail:
            code = "comment_required"
        return RedirectResponse(f"/device/{device_id}/fault/{fault_id}?err={code}",
                                status_code=303)
    except Exception:
        return RedirectResponse(f"/device/{device_id}/fault/{fault_id}?err={code}",
                                status_code=303)
    return RedirectResponse(f"/device/{device_id}/fault/{fault_id}?ok={ok_code or code}",
                            status_code=303)


@rt("/device/{device_id}/fault/{fault_id}/assign")
async def post_assign(req, device_id: str, fault_id: str, assigned_to: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    if not assigned_to:
        return RedirectResponse(f"/device/{device_id}/fault/{fault_id}", status_code=303)
    return await _act(token, fault_id, device_id,
                      lambda: faults_api.assign_fault(token, fault_id, assigned_to), "assign")


@rt("/device/{device_id}/fault/{fault_id}/start")
async def post_start(req, device_id: str, fault_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    return await _act(token, fault_id, device_id,
                      lambda: faults_api.start_fault(token, fault_id), "conflict",
                      ok_code="start")


@rt("/device/{device_id}/fault/{fault_id}/diagnosis")
async def post_diagnosis(req, device_id: str, fault_id: str, diagnosis: str = "",
                         quote_amount: str = "", quote_notes: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    if not (diagnosis or "").strip():
        return RedirectResponse(f"/device/{device_id}/fault/{fault_id}?err=diagnosis", status_code=303)
    amount = None
    if (quote_amount or "").strip():
        try:
            amount = float(quote_amount)
        except ValueError:
            amount = None
    return await _act(token, fault_id, device_id,
                      lambda: faults_api.submit_diagnosis(token, fault_id, diagnosis, amount,
                                                          quote_notes or None), "diagnosis")


@rt("/device/{device_id}/fault/{fault_id}/approval")
async def post_approval(req, device_id: str, fault_id: str, approved: str = "", comment: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    return await _act(token, fault_id, device_id,
                      lambda: faults_api.review_approval(token, fault_id, approved == "yes",
                                                         comment or None), "approval",
                      ok_code="approval" if approved == "yes" else "reject")


@rt("/device/{device_id}/fault/{fault_id}/resolve")
async def post_resolve(req, device_id: str, fault_id: str, resolution_notes: str = "",
                       final_price: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect
    if not (resolution_notes or "").strip():
        return RedirectResponse(f"/device/{device_id}/fault/{fault_id}?err=resolve", status_code=303)
    price = None
    if (final_price or "").strip():
        try:
            price = float(final_price)
        except ValueError:
            price = None
    return await _act(token, fault_id, device_id,
                      lambda: faults_api.resolve_fault(token, fault_id, resolution_notes, price),
                      "resolve")
