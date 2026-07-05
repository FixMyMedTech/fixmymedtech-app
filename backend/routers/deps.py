# deps.py — shared dependencies

from fastapi import HTTPException, Header, Depends
from sqlalchemy import select
from supabase import Client
from sqlalchemy import select
from sqlalchemy.orm import selectinload
# from jwt import PyJWKClient
# import jwt

from config.supabase_config import get_db, AsyncSession
from models.models import Profile

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_API_ANON_KEY")


def get_supabase(request) -> Client:
    return request.app.state.supabase


async def get_current_user(authorization: str = Header(...),
                           db: AsyncSession = Depends(get_db)) -> Profile:
    """
    Validates the Supabase JWT passed as Bearer token.
    Returns the user payload from Supabase.
    """
    from supabase import create_client
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]

    # Use anon client to verify user token
    client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    try:
        user = client.auth.get_user(token)
        
        result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.organization))
            .where(Profile.id == user.user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")
        if not profile.organization_id:
            raise HTTPException(status_code=403, detail="Usuario sin organización asignada")

        return profile
        


        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate token")