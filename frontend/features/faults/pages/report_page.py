from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.helper as auth_helper
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api

from components import *
from components import page_shell, status_badge, fmt_date
import features.auth.api as auth_api
from i18n import t as make_t
rt = APIRouter()

def _severity_text(text: str) -> str:
    if " — " in text:
        level, desc = text.split(" — ", 1)
        return f"{desc} - {level}"
    return text

# ══════════════════════════════════════════════════════════════
# FAULT REPORT
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/report")
async def get(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/report", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        me = await auth_api.get_me(token)
        full_name = me.get("full_name") or req.session.get("user_email", "")
    except Exception:
        full_name = req.session.get("user_email", "")

    content = Div(
        Div(
            A(_("public_qr.back"), href=f"/d/{device_id}",
              style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:block;margin-bottom:16px;"),
            H2(_("report_fault.heading"), style="margin-bottom:6px;"),
            P(_("report_fault.desc"),
              style="margin-bottom:16px;"),
            Div(
                Label(_("report_fault.description_label"), cls="label"),
                Textarea(name="description", cls="input", rows="4",
                         placeholder=_("report_fault.description_placeholder")),
                cls="form-group"
            ),
            Div(
                Label(_("report_fault.severity_label"), cls="label"),
                Div(
                    *[Label(Input(type="radio", name="severity", value=v,
                                  checked=(v=="medium")),
                             f" {_severity_text(_(f'report_fault.severity_{v}'))}",
                             style="display:block;padding:8px 10px;margin-bottom:6px;font-size:0.875rem;cursor:pointer;")
                      for v in ["low", "medium", "high", "critical"]],
                )
            ),
            Div(
                Label(_("report_fault.name_label"), cls="label"),
                Div(full_name, cls="input",
                    style="opacity:.7;"),
                cls="form-group", style="margin-top:12px;"
            ),
            Button(_("report_fault.submit"), type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:8px;"),
            style="padding:16px;"
        ),
        cls="card", style="max-width:560px;margin:24px auto;"
    )

    return page_shell(
        Form(content, method="post", action=f"/d/{device_id}/report"),
        current="/devices", title=_("title.report_fault"), lang=lang
    )


@rt("/d/{device_id}/report")
async def post(req, device_id: str, description: str,
               severity: str = "medium"):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return RedirectResponse(f"/login?next=/d/{device_id}/report", status_code=302)

    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    if not description.strip():
        return RedirectResponse(f"/d/{device_id}/report", status_code=302)

    try:
        me = await auth_api.get_me(token)
        full_name = me.get("full_name") or req.session.get("user_email", "Anonymous")
    except Exception:
        full_name = req.session.get("user_email", "Anonymous")

    try:
        await faults_api.submit_fault_public({
            "device_id": device_id,
            "description": description,
            "severity": severity,
            "reporter_name": full_name,
        })
    except Exception:
        pass

    return page_shell(
        Div(
            Div(
                Div("✓", style="width:52px;height:52px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.3rem;display:flex;align-items:center;justify-content:center;margin:0 auto 14px;"),
                H2(_("report_fault.success_heading")),
                P(_("report_fault.success_msg")),
                A(_("report_fault.success_back"), href=f"/d/{device_id}",
                  cls="btn btn-secondary", style="margin-top:16px;"),
                style="text-align:center;padding:40px 24px;"
            ),
            cls="card", style="max-width:560px;margin:80px auto;"
        ),
        current="/devices", lang=lang
    )
