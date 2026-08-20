import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config.supabase_config import get_db
from models.models import Profile, OrgUser
import ssl
import certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
from jwt import PyJWKClient
import jwt

security = HTTPBearer()

SUPABASE_PROJECT_URL = os.getenv("SUPABASE_URL")
JWKS_URL = f"{SUPABASE_PROJECT_URL}/auth/v1/.well-known/jwks.json"

jwks_client = PyJWKClient(JWKS_URL)


def decode_supabase_jwt(token: str) -> dict:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")


async def get_current_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    payload = decode_supabase_jwt(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin subject")

    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships).selectinload(OrgUser.organization))
        .where(Profile.id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    if not profile.org_memberships:
        raise HTTPException(status_code=403, detail="Usuario sin organización asignada")

    return profile
