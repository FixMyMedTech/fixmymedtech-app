# routers/oauth.py — Social (OAuth2) login via Authlib
#
# Flow:
#  1. Frontend hits GET /api/auth/oauth/{provider}  -> Authlib redirects to provider
#  2. Provider redirects back to /api/auth/oauth/{provider}/callback
#  3. Authlib exchanges code for tokens + fetches user profile (email / name)
#  4. We upsert the user in our LOCAL users table, link to a profile + org, and
#     return a local Authlib JWT that the backend already validates.

import os
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from models.models import Organization, Profile, OrgUser, User
from utils.username import generate_username
from config.users import get_jwt_strategy

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5001")


def _get_oauth():
    """Access the Authlib OAuth instance registered in app state."""
    from config.oauth import oauth
    return oauth


def _success_redirect(access_token: str):
    """Redirect the browser back to the frontend callback route which stores the
    token in the FastHTML session. The token is passed as a short-lived query
    param (single hop between backend and frontend)."""
    return RedirectResponse(
        f"{FRONTEND_URL}/oauth-callback?access_token={access_token}",
        status_code=302,
    )


@router.get("/oauth/{provider}")
async def oauth_start(provider: str, request: Request):
    oauth = _get_oauth()
    client = getattr(oauth, provider, None)
    if client is None:
        raise HTTPException(status_code=404, detail=f"No OAuth provider '{provider}' configured")
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    oauth = _get_oauth()
    client = getattr(oauth, provider, None)
    if client is None:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    try:
        token = await client.authorize_access_token(request)
        userinfo = await client.userinfo(token=token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

    # Normalize userinfo (dict, or an OAuth2Token-like object)
    info = dict(userinfo) if hasattr(userinfo, "items") else userinfo

    email = (info.get("email") or "").strip().lower()
    name = info.get("name") or info.get("preferred_username") or info.get("username") or email.split("@")[0]

    # Discord only returns email when the user has a verified email AND
    # the app requested the "email" scope.  If it's missing we fabricate
    # a placeholder so the upsert can still proceed — but flag it.
    discord_no_email = False
    if not email and provider == "discord":
        discord_no_email = True
        email = f"discord-{info.get('id', 'unknown')}@fixmymedtech.local"

    if not email:
        raise HTTPException(status_code=400, detail="Provider did not return an email")

    # Find-or-create the local user + profile + default org, then mint a local JWT.
    try:
        user_id, access_token = await _upsert_user(db, email, name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not provision user: {str(e)}")

    return _success_redirect(access_token)


async def _upsert_user(db: AsyncSession, email: str, name: str):
    """Find or create a local user + profile + default org. Returns (user_id, jwt)."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        import secrets
        user = User(
            email=email,
            full_name=name,
            hashed_password="!",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

    existing = await db.execute(select(Profile).where(Profile.id == user.id))
    if not existing.scalar_one_or_none():
        username = await generate_username(name, db)
        profile = Profile(id=user.id, username=username, full_name=name)
        db.add(profile)
        await db.flush()

    # Create a default org + admin membership on first run
    org_count = await db.execute(
        select(OrgUser).where(OrgUser.profile_id == user.id)
    )
    if not org_count.scalar_one_or_none():
        org = Organization(name=name, country="", type="hospital")
        db.add(org)
        await db.flush()
        db.add(OrgUser(profile_id=user.id, organization_id=org.id, role="admin"))

    await db.commit()

    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user)
    return str(user.id), access_token