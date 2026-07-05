# routers/auth.py

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from models.models import Profile
from routers.deps import get_supabase
from config.supabase_config import AsyncSession,get_db, supa_client as sb
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

        
        # Create profile
        profile = {
            "id": user_id,
            "full_name": body.full_name,
            "organization_id": body.organization_id,
            "role": body.role,
        }

        # Crear el profile en nuestra DB vía SQLAlchemy
        profile = Profile(
            id=user_id,
            full_name=body.full_name,
            organization_id=body.organization_id,
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