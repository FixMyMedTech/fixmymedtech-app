# routers/auth.py

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from models.models import Organization, Profile
from routers.deps import get_supabase
from config.supabase_config import AsyncSession,get_db, supa_client as sb
from utils.profile import get_current_profile
import uuid
router = APIRouter()

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
    print(request)
    sb = get_supabase(request)
    try:
        res = sb.auth.sign_up({"email": body.email, "password": body.password,
                "options": {
                        "email_redirect_to": f"{FRONTEND_URL}/login"
                    }
        })
        user_id = res.user.id

        # Auto-create an organization if the user didn't pick one
        if body.organization_id:
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
            raise HTTPException(status_code=400, detail=f"Error creating profile: {str(e)}")

        return {"message": "Account created. Check your email to confirm."}
 
    except Exception as e:
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