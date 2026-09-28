# routers/organizations.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import select, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.profile import get_current_profile
from config.db_config import get_db
from models.models import Organization, Profile, OrgUser, User, Device

router = APIRouter()

VALID_MEMBER_ROLES = ("admin", "technician", "clinical_staff", "engineering_staff")


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None


class MemberRoleUpdate(BaseModel):
    role: str


class MemberAdd(BaseModel):
    profile_id: str
    role: str = "technician"


class MemberInvite(BaseModel):
    email: EmailStr
    role: str = "technician"


@router.get("/")
async def list_organizations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).order_by(Organization.name))
    return result.scalars().all()


@router.get("/my_organizations")
async def get_my_organizations(
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Organization)
        .join(OrgUser, OrgUser.organization_id == Organization.id)
        .where(OrgUser.profile_id == profile.id)
        .order_by(Organization.name)
    )
    orgs = result.scalars().all()
    if not orgs:
        raise HTTPException(status_code=403, detail="No organizations found")
    device_org_ids = set((await db.execute(
        select(Device.organization_id).where(or_(
            Device.organization_id.in_([o.id for o in orgs]),
            Device.organization_maintenance_id.in_([o.id for o in orgs]),
            Device.healthsite_id.in_([o.id for o in orgs]),
        ))
    )).scalars().all())
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "country": o.country,
            "region": o.region,
            "address": o.address,
            "type": o.type,
            "contact_email": o.contact_email,
            "osm_id": o.osm_id,
            "osm_type": o.osm_type,
            "source": o.source,
            "role": profile.get_role_for_org(o.id),
            "has_devices": o.id in device_org_ids,
        }
        for o in orgs
    ]


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only organization admins can delete organizations")

    result = await db.execute(select(Organization).where(Organization.id == org_uuid))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    devices = await db.scalar(
        select(Device.id).where(or_(
            Device.organization_id == org_uuid,
            Device.organization_maintenance_id == org_uuid,
            Device.healthsite_id == org_uuid,
        )).limit(1)
    )
    if devices:
        raise HTTPException(status_code=400, detail="Organization has registered devices")

    await db.execute(delete(OrgUser).where(OrgUser.organization_id == org_uuid))
    await db.delete(org)
    await db.commit()
    return {"message": "Organization deleted"}


def _member_org_check(profile: Profile, org_uuid) -> None:
    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only organization admins can manage members")


@router.get("/{org_id}/members")
async def get_organization_members(
    org_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view organization members")

    result = await db.execute(
        select(Profile, User.email, OrgUser.role)
        .join(OrgUser, OrgUser.profile_id == Profile.id)
        .join(User, User.id == Profile.id)
        .where(OrgUser.organization_id == org_uuid)
        .order_by(Profile.full_name, Profile.username)
    )
    return [
        {
            "id": str(member.id),
            "name": member.full_name or member.username,
            "username": member.username,
            "email": email,
            "role": role,
        }
        for member, email, role in result.all()
    ]


@router.get("/{org_id}/search_profiles")
async def search_profiles(
    org_id: str,
    q: str = "",
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only admins can search profiles")

    query = q.strip()
    existing = select(OrgUser.profile_id).where(OrgUser.organization_id == org_uuid)
    stmt = (
        select(Profile, User.email)
        .join(User, User.id == Profile.id)
        .where(Profile.id.not_in(existing))
        .order_by(Profile.full_name, Profile.username)
    )
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                Profile.full_name.ilike(pattern),
                Profile.username.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    stmt = stmt.limit(20)
    result = await db.execute(stmt)
    return [
        {
            "id": str(profile_row.id),
            "username": profile_row.username,
            "full_name": profile_row.full_name,
            "email": email,
        }
        for profile_row, email in result.all()
    ]


@router.post("/{org_id}/members")
async def add_organization_member(
    org_id: str,
    body: MemberAdd,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
        member_uuid = _uuid.UUID(body.profile_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization or profile id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add organization members")

    if body.role not in VALID_MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Invalid organization role")

    existing = await db.execute(
        select(OrgUser).where(
            OrgUser.organization_id == org_uuid,
            OrgUser.profile_id == member_uuid,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Profile is already an organization member")

    profile_exists = await db.execute(
        select(Profile).where(Profile.id == member_uuid)
    )
    if not profile_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Profile not found")

    db.add(OrgUser(
        profile_id=member_uuid,
        organization_id=org_uuid,
        role=body.role,
    ))
    await db.commit()
    return {"message": "Organization member added"}


def _username_base(email: str) -> str:
    local = email.split("@")[0].lower()
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in local)
    return (cleaned.strip("._-") or "user")[:60]


async def _unique_username(db: AsyncSession, base: str) -> str:
    candidate = base
    suffix = 1
    while await db.scalar(select(Profile.id).where(Profile.username == candidate)):
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


@router.post("/{org_id}/invite")
async def invite_organization_member(
    org_id: str,
    body: MemberInvite,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to the organization and email them a link to set a password.

    Works both for people who already have a FixMyMedTech account and for those
    who do not: a missing account is created (verified, with a random password
    that the emailed link replaces) and joined to this organization.
    """
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only admins can invite users")

    if body.role not in VALID_MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Invalid organization role")

    email = str(body.email).strip().lower()

    if not await db.scalar(select(Organization.id).where(Organization.id == org_uuid)):
        raise HTTPException(status_code=404, detail="Organization not found")

    # Case-insensitive: avoids a unique-constraint error on legacy mixed-case rows.
    user = await db.scalar(select(User).where(func.lower(User.email) == email))
    created_user = False

    if user:
        already_member = await db.scalar(
            select(OrgUser.id).where(
                OrgUser.organization_id == org_uuid,
                OrgUser.profile_id == user.id,
            )
        )
        if already_member:
            raise HTTPException(status_code=409, detail="User is already an organization member")
    else:
        from pwdlib import PasswordHash
        from pwdlib.hashers.bcrypt import BcryptHasher
        user = User(
            email=email,
            hashed_password=PasswordHash(hashers=[BcryptHasher()]).hash(_uuid.uuid4().hex),
            is_active=True,
            is_superuser=False,
            # The emailed link authenticates them, so no separate verification step.
            is_verified=True,
            full_name=email.split("@")[0].replace(".", " ").title(),
        )
        db.add(user)
        await db.flush()
        db.add(Profile(
            id=user.id,
            username=await _unique_username(db, _username_base(email)),
            full_name=user.full_name,
        ))
        created_user = True

    db.add(OrgUser(profile_id=user.id, organization_id=org_uuid, role=body.role))
    await db.commit()

    # Password-setup link, using the fastapi-users reset-password contract.
    from fastapi_users.jwt import generate_jwt
    from config.email import send_invitation_email
    from config.users import FRONTEND_URL, JWT_SECRET, _password_helper

    email_sent = True
    try:
        token = generate_jwt(
            {
                "sub": str(user.id),
                "password_fgpt": _password_helper.hash(user.hashed_password),
                "aud": "fastapi-users:reset",
            },
            JWT_SECRET,
            3600,
        )
        await send_invitation_email(email, token, FRONTEND_URL)
    except Exception:
        import logging
        logging.getLogger("email").exception("Failed to send invitation email to %s", email)
        email_sent = False

    return {
        "message": "Invitation sent",
        "email": email,
        "created_user": created_user,
        "email_sent": email_sent,
    }


@router.delete("/{org_id}/members/me")
async def leave_organization(
    org_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    result = await db.execute(
        select(OrgUser).where(
            OrgUser.organization_id == org_uuid,
            OrgUser.profile_id == profile.id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization membership not found")

    if membership.role == "admin":
        admin_count = await db.scalar(
            select(func.count()).select_from(OrgUser).where(
                OrgUser.organization_id == org_uuid,
                OrgUser.role == "admin",
            )
        )
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Add another organization admin before leaving")

    await db.delete(membership)
    await db.commit()
    return {"message": "You left the organization"}


@router.delete("/{org_id}/members/{member_id}")
async def remove_organization_member(
    org_id: str,
    member_id: str,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
        member_uuid = _uuid.UUID(member_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization or member id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove organization members")

    result = await db.execute(
        select(OrgUser).where(
            OrgUser.organization_id == org_uuid,
            OrgUser.profile_id == member_uuid,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization member not found")

    await db.delete(membership)
    await db.commit()
    return {"message": "Organization member removed"}


@router.patch("/{org_id}/members/{member_id}")
async def update_organization_member(
    org_id: str,
    member_id: str,
    body: MemberRoleUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
        member_uuid = _uuid.UUID(member_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization or member id")

    if profile.get_role_for_org(org_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change organization roles")
    if body.role not in ("admin", "technician", "clinical_staff", "engineering_staff"):
        raise HTTPException(status_code=400, detail="Invalid organization role")

    result = await db.execute(
        select(OrgUser).where(
            OrgUser.organization_id == org_uuid,
            OrgUser.profile_id == member_uuid,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Organization member not found")

    membership.role = body.role
    await db.commit()
    return {"message": "Organization member role updated"}


@router.patch("/{org_id}")
async def update_organization(
    org_id: str,
    body: OrgUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        org_uuid = _uuid.UUID(org_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization id")

    role = profile.get_role_for_org(org_uuid)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit organizations")

    result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if body.name is not None:
        org.name = body.name
    if body.type is not None:
        if body.type not in ("hospital", "clinic", "health_centre", "lab", "engineering"):
            raise HTTPException(status_code=400, detail="Invalid organization type")
        org.type = body.type
    if body.country is not None:
        org.country = body.country
    if body.region is not None:
        org.region = body.region
    if body.address is not None:
        org.address = body.address
    if body.contact_email is not None:
        org.contact_email = body.contact_email

    await db.commit()
    await db.refresh(org)
    return {
        "id": str(org.id),
        "name": org.name,
        "country": org.country,
        "region": org.region,
        "address": org.address,
        "contact_email": org.contact_email,
    }
