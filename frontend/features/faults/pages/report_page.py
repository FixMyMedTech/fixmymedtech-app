from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import auth.helper as auth_helper
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api

from components import *

rt = APIRouter()
from components import page_shell, status_badge, fmt_date, pub_shell

# ══════════════════════════════════════════════════════════════
# PUBLIC FAULT REPORT
# ══════════════════════════════════════════════════════════════

@rt("/d/{device_id}/report")
async def get(req, device_id: str):
    content = Div(
        Div(Div(Span("✚", cls="pub-cross"), " FixMyMedTech", cls="pub-logo"), cls="pub-header"),
        Div(
            A("← Back to device", href=f"/d/{device_id}",
              style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;display:block;margin-bottom:16px;"),
            H2("Report a fault", style="margin-bottom:6px;"),
            P("No account needed. Your report goes directly to the biomed team.",
              style="margin-bottom:16px;"),
            Div(
                Label("Describe the problem *", cls="label"),
                Textarea(name="description", cls="input", rows="4",
                         placeholder="What is wrong with the device?"),
                cls="form-group"
            ),
            Div(
                Label("Severity", cls="label"),
                Div(
                    *[Label(Input(type="radio", name="severity", value=v,
                                  checked=(v=="medium")), f" {l}",
                             style="display:block;padding:8px 10px;border:1px solid var(--c-border);border-radius:var(--r-md);margin-bottom:6px;font-size:0.875rem;cursor:pointer;")
                      for v, l in [
                          ("low",      "Low — minor issue, device still usable"),
                          ("medium",   "Medium — needs attention"),
                          ("high",     "High — device partially unusable"),
                          ("critical", "Critical — device completely down"),
                      ]],
                )
            ),
            Div(
                Label("Your name (optional)", cls="label"),
                Input(name="reporter_name", cls="input", placeholder="Nurse / Technician name"),
                cls="form-group", style="margin-top:12px;"
            ),
            Button("Submit fault report", type="submit", cls="btn btn-primary",
                   style="width:100%;justify-content:center;margin-top:8px;"),
            style="padding:16px;"
        ),
        cls="pub-page",
        method="post", action=f"/d/{device_id}/report"
    )

    return pub_shell(
        Form(content, method="post", action=f"/d/{device_id}/report"),
        title="Report fault — FixMyMedTech"
    )


@rt("/d/{device_id}/report")
async def post(req, device_id: str, description: str,
               severity: str = "medium", reporter_name: str = ""):
    if not description.strip():
        return RedirectResponse(f"/d/{device_id}/report", status_code=302)

    try:
        await faults_api.submit_fault_public({
            "device_id": device_id,
            "description": description,
            "severity": severity,
            "reporter_name": reporter_name or "Anonymous",
        })
    except Exception:
        pass

    return pub_shell(
        Div(
            Div(Div(Span("✚", cls="pub-cross"), " FixMyMedTech", cls="pub-logo"), cls="pub-header"),
            Div(
                Div("✓", style="width:52px;height:52px;background:var(--c-green-lt);color:var(--c-green);border-radius:50%;font-size:1.3rem;display:flex;align-items:center;justify-content:center;margin:0 auto 14px;"),
                H2("Report submitted"),
                P("A technician will be notified. Thank you for helping keep this equipment working."),
                A("← Back to device", href=f"/d/{device_id}",
                  cls="btn btn-secondary", style="margin-top:16px;"),
                style="text-align:center;padding:40px 24px;"
            ),
            cls="pub-page"
        )
    )
