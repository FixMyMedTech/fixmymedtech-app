# routers/auth.py — Auth endpoints backed by FastAPI-Users + fastapi-mail
#
# Keeps the same frontend contract:
#   POST /api/auth/login    → {access_token, user: {id, email}}
#   POST /api/auth/signup   → {message}
#   POST /api/auth/logout   → {message}
#   GET  /api/auth/me       → {id, username, full_name, organizations}
#   PATCH /api/auth/me      → {id, username, full_name}
#   GET  /api/auth/tasks    → [...]

from fastapi import APIRouter, HTTPException, Request, Depends
from starlette.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid
import logging

from models.models import Organization, Profile, OrgUser, User, FaultReport, MaintenanceLog
from config.db_config import get_db
from config.users import (
    get_user_manager,
    UserManager,
    fastapi_users,
    current_active_user,
    auth_backend,
)
from fastapi_users.exceptions import UserAlreadyExists, UserNotExists
from utils.username import generate_username

router = APIRouter()
logger = logging.getLogger(__name__)

FRONTEND_URL = Optional[str]


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


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    body: LoginRequest,
    user_manager: UserManager = Depends(get_user_manager),
):
    import os
    from fastapi_users.authentication import JWTStrategy
    from config.users import get_jwt_strategy

    # 1. Fetch user by email
    try:
        user = await user_manager.get_by_email(body.email.lower())
    except UserNotExists:
        raise HTTPException(status_code=404, detail="user_not_found")
    except Exception:
        raise HTTPException(status_code=404, detail="user_not_found")

    # 2. Verify password via FastAPI-Users' password helper (bcrypt, argon2, …)
    valid, new_hash = user_manager.password_helper.verify_and_update(
        body.password, user.hashed_password
    )
    if not valid:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    # Rotate hash if the hasher format changed (e.g. argon2→bcrypt migration)
    if new_hash is not None:
        user.hashed_password = new_hash
        # user_manager.update is async but we don't await — it's optional here

    # 3. Mint JWT via FastAPI-Users' strategy
    strategy = get_jwt_strategy()
    token = await strategy.write_token(user)

    return {
        "access_token": token,
        "user": {
            "id": str(user.id),
            "email": user.email,
        },
    }


# ── Signup ─────────────────────────────────────────────────────────────────────

@router.post("/signup")
async def signup(
    body: SignupRequest,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
    db: AsyncSession = Depends(get_db),
):
    from fastapi_users.schemas import BaseUserCreate

    email = body.email.lower()

    # 1. Create user via FastAPI-Users (hashes password, fires on_after_register hook)
    try:
        user_create = BaseUserCreate(
            email=email,
            password=body.password,
        )
        user = await user_manager.create(user_create, safe=False, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=409, detail="user_already_exists")
    except Exception as exc:
        logger.exception("UserManager.create failed for %s", email)
        raise HTTPException(status_code=400, detail=f"Signup failed: {exc}")

    # 2. Create Profile (1:1 with user)
    username = await generate_username(body.full_name, db)
    profile = Profile(
        id=user.id,
        username=username,
        full_name=body.full_name,
    )
    db.add(profile)
    await db.flush()

    # 3. Create or link Organization
    if body.organization_id:
        try:
            org_uuid = uuid.UUID(body.organization_id)
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid organization id")
        res = await db.execute(
            select(Organization).where(Organization.id == org_uuid)
        )
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Selected organization does not exist")
        org_id = str(org_uuid)
    else:
        org = Organization(
            name=body.full_name,
            country=body.country or "",
            type="hospital",
        )
        db.add(org)
        await db.flush()
        org_id = str(org.id)

    db.add(OrgUser(
        profile_id=user.id,
        organization_id=org_id,
        role=body.role,
    ))

    await db.commit()
    return {"message": "Account created."}


# ── Logout (stateless — client discards token) ─────────────────────────────────

@router.post("/logout")
async def logout():
    return {"message": "Logged out"}


# ── Me ─────────────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.org_memberships).selectinload(OrgUser.organization))
        .where(Profile.id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
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
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

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


# ── Tasks ──────────────────────────────────────────────────────────────────────

@router.get("/tasks")
async def my_tasks(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    uid = user.id

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


# ── Verify (email confirmation) ───────────────────────────────────────────────

@router.get("/verify")
async def verify_email(
    token: str,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
):
    import os
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5001").rstrip("/")
    try:
        await user_manager.verify(token)
        return RedirectResponse(f"{frontend_url}/login?verified=1", status_code=302)
    except Exception:
        return RedirectResponse(f"{frontend_url}/login?verified=0", status_code=302)


# ── Request verification (resend) ─────────────────────────────────────────────

@router.post("/request-verification")
async def request_verification(
    body: LoginRequest,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await user_manager.get_by_email(body.email.lower())
    except Exception:
        # Silently return to avoid leaking email existence
        return {"message": "If your email is registered, a verification link has been sent."}

    if user.is_verified:
        return {"message": "Account is already verified."}

    await user_manager.request_verify(user, request=request)
    return {"message": "If your email is registered, a verification link has been sent."}


# ── Forgot / reset password ───────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body: LoginRequest,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await user_manager.get_by_email(body.email.lower())
        await user_manager.forgot_password(user, request=request)
    except Exception:
        pass  # Always return the same response to avoid leaking
    return {"message": "If your email is registered, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    token: str,
    password: str,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        await user_manager.reset_password(token, password)
        return {"message": "Password has been reset."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Reset failed: {exc}")
