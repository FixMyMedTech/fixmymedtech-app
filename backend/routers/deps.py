# deps.py — shared dependencies

from fastapi import HTTPException, Header, Depends
from supabase import Client
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db, AsyncSession
from models.models import Profile, OrgUser

import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_API_ANON_KEY")


def get_supabase(request) -> Client:
    return request.app.state.supabase


async def get_current_user(authorization: str = Header(...),
                           db: AsyncSession = Depends(get_db)) -> Profile:
    from supabase import create_client
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]

    client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    try:
        user = client.auth.get_user(token)

        result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.org_memberships).selectinload(OrgUser.organization))
            .where(Profile.id == user.user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")
        if not profile.org_memberships:
            raise HTTPException(status_code=403, detail="Usuario sin organización asignada")

        return profile
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate token")
