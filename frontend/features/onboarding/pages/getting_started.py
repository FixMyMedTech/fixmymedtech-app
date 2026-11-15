# pages/getting_started.py — /getting-started
#
# Kept as a signpost only (old links, signup and invitation redirects): the
# page itself is gone from the menu. "Getting started" is the three welcome
# quests on /community/start/quests (features/community); once they are done
# it disappears and the next step is /invite-clinic, which also lists the
# clinics that named this engineer. Re-reads /api/auth/me so the session
# (sidebar, page gate) follows a talk confirmed by a host in the meantime.

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.onboarding.api as ob_api

rt = APIRouter()


@rt("/getting-started")
async def get(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    # /api/onboarding/me first: it promotes an applicant whose quests are all
    # done, and the session refresh after it then sees the new status.
    try:
        await ob_api.get_me(token)
    except Exception:
        pass
    user = await auth_helper.refresh_onboarding(req, token)
    if user.get("account_kind") == "clinic":
        return RedirectResponse("/clinic/setup", status_code=302)
    if user.get("member_status") in ("applicant", "refused"):
        return RedirectResponse("/community/start/quests", status_code=302)
    return RedirectResponse("/invite-clinic", status_code=302)
