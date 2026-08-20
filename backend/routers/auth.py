# routers/auth.py

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from typing import Optional
from models.models import Organization, Profile, OrgUser, FaultReport, MaintenanceLog, Device
from routers.deps import get_supabase
from config.supabase_config import AsyncSession, get_db, supa_client as sb
from utils.profile import get_current_profile
from utils.username import generate_username
from sqlalchemy.orm import selectinload
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
    role: str = "admin"


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None


@router.post("/login")
async def login(body: LoginRequest, request: Request,
                db: AsyncSession = Depends(get_db)):
    sb = get_supabase(request)

    # Check if user exists in auth.users before attempting login
    db_user = await db.execute(
        text("SELECT id FROM auth.users WHERE email = :email"),
        {"email": body.email},
    )
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="user_not_found")

    try:
        res = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token": res.session.access_token,
            "user": {
                "id": res.user.id,
                "email": res.user.email,
            }
        }
    except Exception as e:
        msg = str(e).lower()
        if "email not confirmed" in msg or "not confirmed" in msg:
            raise HTTPException(status_code=403, detail="email_not_confirmed")
        raise HTTPException(status_code=401, detail="invalid_credentials")


@router.post("/signup")
async def signup(body: SignupRequest, request: Request,
                 db: AsyncSession = Depends(get_db)):

    sb = get_supabase(request)
    try:
        email_redirect_to = f"{FRONTEND_URL.rstrip('/')}/login" if FRONTEND_URL else None
        res = sb.auth.sign_up({
            "email": body.email, "password": body.password,
            "options": ({"email_redirect_to": email_redirect_to}
                        if email_redirect_to else None),
        })

        if res.user and res.user.confirmed_at:
            raise HTTPException(status_code=409, detail="user_already_exists")

        user_id = res.user.id

        db_user = await db.execute(
            text("SELECT id FROM auth.users WHERE id = :uid"), {"uid": user_id}
        )
        if not db_user.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=(
                    "User already exists. Please log in."
                ),
            )

        username = await generate_username(body.full_name, db)

        profile = Profile(
            id=user_id,
            username=username,
            full_name=body.full_name,
        )
        db.add(profile)
        await db.flush()

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
            org = Organization(
                name=body.full_name,
                country=body.country or "",
                type="hospital",
            )
            db.add(org)
            await db.flush()
            org_id = str(org.id)

        org_user = OrgUser(
            profile_id=user_id,
            organization_id=org_id,
            role=body.role,
        )
        db.add(org_user)

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
        detail = str(e)
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                detail = resp.text or detail
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=detail)


@router.post("/logout")
async def logout(request: Request):
    sb = get_supabase(request)
    sb.auth.sign_out()
    return {"message": "Logged out"}


@router.get("/me")
async def me(profile: Profile = Depends(get_current_profile)):
    return {
        "id": profile.id,
        "username": profile.username,
        "full_name": profile.full_name,
        "organizations": [
            {
                "id": m.organization_id,
                "name": m.organization.name if m.organization else None,
                "country": m.organization.country if m.organization else None,
                "role": m.role,
            }
            for m in profile.org_memberships
        ],
    }


@router.patch("/me")
async def update_me(
    body: ProfileUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        profile.full_name = body.full_name
    if body.username is not None:
        candidate = body.username.strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        existing = await db.execute(
            text("SELECT 1 FROM fixmymedtech.profiles WHERE username = :u AND id != :id"),
            {"u": candidate, "id": str(profile.id)},
        )
        if existing.scalar():
            raise HTTPException(status_code=400, detail="Username already taken")
        profile.username = candidate
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": profile.id,
        "username": profile.username,
        "full_name": profile.full_name,
    }


@router.get("/tasks")
async def my_tasks(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    uid = profile.id

    faults_result = await db.execute(
        select(FaultReport)
        .options(selectinload(FaultReport.device))
        .where(FaultReport.assigned_to == uid)
        .order_by(FaultReport.reported_at.desc())
    )
    faults = [
        {
            "id": str(f.id),
            "type": "fault",
            "title": f.device.name if f.device else "Unknown device",
            "description": f.description,
            "severity": f.severity,
            "status": f.status,
            "date": f.reported_at.isoformat() if f.reported_at else None,
            "device_id": str(f.device_id),
        }
        for f in faults_result.scalars().all()
    ]

    logs_result = await db.execute(
        select(MaintenanceLog)
        .options(selectinload(MaintenanceLog.device))
        .where(MaintenanceLog.assigned_to == uid)
        .order_by(MaintenanceLog.performed_at.desc())
    )
    logs = [
        {
            "id": str(l.id),
            "type": "maintenance",
            "title": l.device.name if l.device else "Unknown device",
            "description": l.description,
            "severity": l.type,
            "status": l.status,
            "date": l.performed_at.isoformat() if l.performed_at else None,
            "device_id": str(l.device_id),
        }
        for l in logs_result.scalars().all()
    ]

    return faults + logs
