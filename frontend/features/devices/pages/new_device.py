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
rt = APIRouter()
# ══════════════════════════════════════════════════════════════
# NEW DEVICE
# ══════════════════════════════════════════════════════════════


@rt("/devices/new")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    try:
        categories = await devices_api.get_categories(token)
    except Exception:
        categories = []

    cat_options = [Option("— Select category —", value="")]
    cat_options += [Option(f"{c.get('icon','')} {c['name']}", value=c["id"]) for c in categories]

    form = Form(
        A("← Devices", href="/devices",
        style="font-size:0.875rem;color:var(--c-text-3);text-decoration:none;margin-bottom:20px;display:inline-block;"),
        H1("Add new device", style="margin-bottom:4px;"),
        P("Register a medical device to start tracking it", style="margin-bottom:20px;"),
        Div(
            H3("Basic information", style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label("Device name *", cls="label", for_="name"),
                    Input(id="name", name="name", cls="input", placeholder="e.g. Ventilator LTV 1200"),
                    cls="form-group"),
                Div(Label("Category", cls="label", for_="category"),
                    Select(*cat_options, id="category", name="category_id", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label("Manufacturer", cls="label"),
                    Input(name="manufacturer", cls="input", placeholder="e.g. GE Healthcare"),
                    cls="form-group"),
                Div(Label("Model", cls="label"),
                    Input(name="model", cls="input", placeholder="e.g. ProCare B40"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label("Serial number", cls="label"),
                    Input(name="serial_number", cls="input", placeholder="SN-XXXXXX"),
                    cls="form-group"),
                Div(Label("Manufacture year", cls="label"),
                    Input(name="manufacture_year", type="number", cls="input",
                        placeholder="2018", min="1990", max="2030"),
                    cls="form-group"),
                cls="form-row"
            ),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            H3("Location & acquisition", style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(
                Div(Label("Location", cls="label"),
                    Input(name="location", cls="input", placeholder="e.g. ICU / Bed 4"),
                    cls="form-group"),
                Div(Label("Acquisition type", cls="label"),
                    Select(Option("Purchased", value="purchased"),
                        Option("Donated", value="donated"),
                        Option("Leased", value="leased"),
                        name="acquisition_type", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            Div(
                Div(Label("Acquisition date", cls="label"),
                    Input(name="acquisition_date", type="date", cls="input"),
                    cls="form-group"),
                Div(Label("Next maintenance due", cls="label"),
                    Input(name="next_maintenance", type="date", cls="input"),
                    cls="form-group"),
                cls="form-row"
            ),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            H3("Notes", style="font-size:1rem;margin-bottom:14px;color:var(--c-text-2);"),
            Div(Textarea(name="notes", cls="input", placeholder="Any relevant notes…", rows="3"),
                cls="form-group"),
            cls="card", style="margin-bottom:14px;"
        ),
        Div(
            A("Cancel", href="/devices", cls="btn btn-secondary"),
            Button("Register device", type="submit", cls="btn btn-primary"),
            style="display:flex;justify-content:flex-end;gap:10px;"
        ),
        method="post", action="/devices/new",
        style="max-width:720px;"
    )

    return page_shell(form, current="/devices", title="Add device — FixMyMedTech")


@rt("/devices/new")
async def post(req, name: str, manufacturer: str = "", model: str = "",
            serial_number: str = "", category_id: str = "", location: str = "",
            acquisition_type: str = "purchased", acquisition_date: str = "",
            manufacture_year: str = "", next_maintenance: str = "", notes: str = ""):
    token, redirect = require_auth(req)
    if redirect: return redirect

    payload = {"name": name}
    if manufacturer:      payload["manufacturer"]     = manufacturer
    if model:             payload["model"]            = model
    if serial_number:     payload["serial_number"]    = serial_number
    if category_id:       payload["category_id"]      = category_id
    if location:          payload["location"]         = location
    if acquisition_type:  payload["acquisition_type"] = acquisition_type
    if acquisition_date:  payload["acquisition_date"] = acquisition_date
    if manufacture_year:  payload["manufacture_year"] = int(manufacture_year)
    if next_maintenance:  payload["next_maintenance"] = next_maintenance
    if notes:             payload["notes"]            = notes

    try:
        device = await devices_api.create_device(token, payload)
        return RedirectResponse(f"/devices/{device['id']}", status_code=302)
    except Exception as e:
        return RedirectResponse("/devices/new", status_code=302)
