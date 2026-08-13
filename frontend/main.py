from atexit import register

from fasthtml.common import FastHTML,serve, fast_app
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv
from fasthtml.common import *

load_dotenv()

from features.dashboard import pages as dashboard
from features.devices.pages import device_list,device_detail,new_device,public_qr_page,guides,maintenance_log
from features.auth.pages import login as auth
from features.faults.pages import report_page
from i18n import LANGUAGES

SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-production")

app, route = fast_app(secret_key=SECRET,
                      static="/static/",
                      live=True,
                      hdrs=(
                        Script(src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"),
                        Link(rel="icon", href="/favicon.ico"),
                    )
    )
                    
# put favicon.ico in your project root or /static
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=SECRET)

@route("/lang")
async def post(req):
    form = await req.form()
    lang = form.get("lang", "en")
    if lang in LANGUAGES:
        req.session["lang"] = lang
    referer = req.headers.get("Referer", "/")
    return RedirectResponse(referer, status_code=302)

auth.rt.to_app(app)
device_detail.rt.to_app(app)
device_list.rt.to_app(app)
dashboard.rt.to_app(app)
public_qr_page.rt.to_app(app)
new_device.rt.to_app(app)
report_page.rt.to_app(app)
maintenance_log.rt.to_app(app)
guides.rt.to_app(app)

serve()