# routers/auth.py

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from typing import Optional
from models.models import Organization, Profile
from routers.deps import get_supabase
from config.supabase_config import AsyncSession,get_db, supa_client as sb
from utils.profile import get_current_profile
import uuid
import logging
router = APIRouter()

logger = logging.getLogger(__name__)

import os

FRONTEND_URL = os.getenv("FRONTEND_URL")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    country: Optional[str] = None
    role: str = "clinical_staff"




@router.post("/login")
async def login(body: LoginRequest, request: Request,
                db: AsyncSession = Depends(get_db)):
    sb = get_supabase(request)
    try:
        res = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
        print(res)
        return {
            "access_token": res.session.access_token,
            "user": {
                "id": res.user.id,
                "email": res.user.email,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/signup")
async def signup(body: SignupRequest, request: Request, 
                 db: AsyncSession = Depends(get_db)):

    print(body)
    sb = get_supabase(request)
    try:
        email_redirect_to = f"{FRONTEND_URL.rstrip('/')}/login" if FRONTEND_URL else None
        res = sb.auth.sign_up({
            "email": body.email, "password": body.password,
            "options": ({"email_redirect_to": email_redirect_to}
                        if email_redirect_to else None),
        })
        user_id = res.user.id

        # Auto-create an organization if the user didn't pick one
        if body.organization_id:
            try:
                org_uuid = uuid.UUID(body.organization_id)
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(status_code=400, detail="Invalid organization id")
            res = await db.execute(
                select(Organization).where(Organization.id == org_uuid)
            )
            if not res.scalar_one_or_none():
                raise HTTPException(status_code=400,
                                    detail="Selected organization does not exist")
            org_id = body.organization_id
        else:
            org_name = body.organization_name or f"{body.full_name}'s Organization"
            org = Organization(
                name=org_name,
                country=body.country or "",
                type="hospital",
            )
            db.add(org)
            await db.flush()
            org_id = str(org.id)

        # Crear el profile en nuestra DB vía SQLAlchemy
        profile = Profile(
            id=user_id,
            full_name=body.full_name,
            organization_id=org_id,
            role=body.role,
        )
        db.add(profile)

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.exception("Profile creation failed for %s", body.email)
            raise HTTPException(status_code=400, detail=f"Error creating profile: {str(e)}")

        return {"message": "Account created. Check your email to confirm."}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Signup failed for %s", getattr(body, "email", "?"))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(request: Request):
    sb = get_supabase(request)
    sb.auth.sign_out()
    return {"message": "Logged out"}


@router.get("/me")
async def me(profile: Profile = Depends(get_current_profile)):
    return {
        "id": profile.id,
        "full_name": profile.full_name,
        "role": profile.role,
        "organization_id": profile.organization_id,
        "organization_name": profile.organization.name if profile.organization else None,
    }