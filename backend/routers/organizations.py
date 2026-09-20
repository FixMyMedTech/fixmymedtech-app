# routers/organizations.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
