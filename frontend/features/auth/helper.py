from fasthtml.common import *
from starlette.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()

# __ API imports __
import features.auth.api as auth_api
import features.dashboard.api as dashboard_api

# ── Auth helpers ─────────────────────────────────────────────

def get_token(req):
    return req.session.get("token")

def clear_session(req):
    """Clear all session data — call when token is invalid/expired."""
    req.session.clear()

async def verify_token(req) -> bool:
    """
    Verify the token is still valid by calling a lightweight API endpoint.
    Returns True if valid, False if expired or invalid.
    """
    token = get_token(req)
    if not token:
        return False
    try:
        await dashboard_api.get_dashboard_stats(token)
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_session(req)
            return False
        return True  # other errors (500 etc) don't mean token is invalid
    except Exception:
        return True  # network errors don't mean token is invalid

def require_auth(req):
    """
    Fast check — just verifies session has a token.
    For full token validation use require_auth_verified.
    """
    token = get_token(req)
    if not token:
        return None, RedirectResponse("/login", status_code=302)
    return token, None

async def require_auth_verified(req):
    """
    Full check — verifies token is still valid with the API.
    Use on sensitive routes like dashboard.
    """
    token = get_token(req)
    if not token:
        return None, RedirectResponse("/login", status_code=302)
    try:
        # Validate by hitting a protected endpoint
        await dashboard_api.get_dashboard_stats(token)
        return token, None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            clear_session(req)
            return None, RedirectResponse("/login?expired=1", status_code=302)
        return token, None
    except Exception:
        return token, None