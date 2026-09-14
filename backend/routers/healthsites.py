# routers/healthsites.py
# Healthsites live in the SAME table as organizations: an organization row IS a
# facility/site. This router manages the healthsites.io-specific parts:
#   - manual creation of a site  (source = 'app', creator becomes admin member)
#   - bulk import from healthsites.io (source = 'healthsites.io')
#   - edits / deletion of site rows
#
# The healthsites.io API key lives in .env as HEALTHSITES_API_KEY.

import math
import os
import uuid as _uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from config.db_config import get_db
from models.models import Device, Organization, OrgUser, Profile
from utils.profile import get_current_profile

router = APIRouter()

HEALTHSITES_API_URL = "https://healthsites.io/api/v3/facilities/"
DEFAULT_IMPORT_RADIUS_KM = 2.0
MAX_IMPORT_RESULTS = 40
IMPORT_TYPES = ("hospital", "clinic", "health_centre", "lab", "engineering")

# healthsites.io subtype -> platform organization type
SUBTYPE_ALIASES = {
    "health_center": "health_centre",
    "doctors": "clinic",
    "doctoc": "clinic",
    "dentist": "clinic",
    "pharmacy": "clinic",
    "drugstore": "clinic",
    "laboratory": "lab",
}


def _bbox(lat: float, lng: float, radius_km: float) -> str:
    dlat = radius_km / 111.32
    dlng = radius_km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    return f"{lng - dlng},{lat - dlat},{lng + dlng},{lat + dlat}"


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two WGS84 points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _extract(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    props = item.get("attributes") or item.get("properties") or {}
    name = str(props.get("name") or item.get("name") or "").strip()
    if not name:
        return None

    lat = lng = None
    centroid = item.get("centroid") or item.get("geometry") or {}
    if isinstance(centroid, dict):
        coords = centroid.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            try:
                lng, lat = float(coords[0]), float(coords[1])
            except (TypeError, ValueError):
                lat = lng = None
    if lat is None or lng is None:
        try:
            lat = float(item.get("lat") or props.get("lat"))
            lng = float(item.get("lon") or item.get("lng") or props.get("lon") or props.get("lng"))
        except (TypeError, ValueError):
            lat = lng = None
    if lat is None or lng is None:
        return None

    osm_id = item.get("osm_id") or props.get("osm_id")
    osm_type = item.get("osm_type") or props.get("osm_type") or "node"
    if not osm_id:
        return None

    subtype = str(props.get("amenity") or item.get("amenity")
                  or props.get("healthcare") or item.get("healthcare")
                  or props.get("health_amenity_type") or item.get("health_amenity_type") or "").strip()
    org_type = SUBTYPE_ALIASES.get(subtype, subtype)
    if org_type not in IMPORT_TYPES:
        org_type = "clinic"

    return {
        "osm_id": str(osm_id),
        "osm_type": str(osm_type),
        "name": name,
        "lat": lat,
        "lng": lng,
        "country": str(item.get("country") or props.get("country") or ""),
        "type": org_type,
    }


def _org_dict(o: Organization) -> dict:
    return {
        "id": str(o.id),
        "name": o.name,
        "country": o.country,
        "region": o.region,
        "type": o.type,
        "contact_email": o.contact_email,
        "osm_id": o.osm_id,
        "osm_type": o.osm_type,
        "latitude": o.latitude,
        "longitude": o.longitude,
        "source": o.source,
    }


# ── schemas ─────────────────────────────────────────────────

class HealthsiteCreate(BaseModel):
    name: str
    country: Optional[str] = ""
    type: Optional[str] = "clinic"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HealthsiteUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SearchBody(BaseModel):
    lat: float
    lng: float
    radius_km: float = Field(default=DEFAULT_IMPORT_RADIUS_KM, gt=0, le=2.0)


class FacilityCandidate(BaseModel):
    osm_id: str
    osm_type: str
    name: str
    country: Optional[str] = ""
    type: Optional[str] = "clinic"
    lat: Optional[float] = None
    lng: Optional[float] = None


class ImportBody(BaseModel):
    facility: FacilityCandidate


# ── manual creation (source='app', creator becomes admin) ─────

@router.post("/")
async def create_healthsite(
    body: HealthsiteCreate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    if body.type not in IMPORT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid site type")

    org = Organization(
        name=body.name.strip(),
        country=(body.country or "").strip(),
        type=body.type,
        latitude=body.latitude,
        longitude=body.longitude,
        source="app",
    )
    db.add(org)
    await db.flush()

    db.add(OrgUser(
        profile_id=profile.id,
        organization_id=org.id,
        role="admin",
    ))
    await db.commit()
    await db.refresh(org)
    return _org_dict(org)


# ── search healthsites.io (returns candidates) ──────────────

@router.post("/search")
async def search_healthsites(
    body: SearchBody,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    api_key = os.getenv("HEALTHSITES_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="No healthsites.io API key configured on the server")

    params = {
        "api-key": api_key,
        "page": "1",
        "extent": _bbox(body.lat, body.lng, body.radius_km),
        "tag-format": "osm",
        "output": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(HEALTHSITES_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"healthsites.io request failed: {e}")

    raw = data if isinstance(data, list) else (
        data.get("results") or data.get("features") or data.get("facilities") or []
    )

    # extract candidates from ALL raw items (API returns pharmacies first;
    # truncating here would hide hospitals), dedupe by (osm_id, osm_type)
    results = []
    seen = set()
    for item in raw:
        fac = _extract(item)
        if not fac:
            continue
        key = (fac["osm_id"], fac["osm_type"])
        if key in seen:
            continue
        seen.add(key)
        results.append(fac)

    # single batched query for already-imported flags
    if results:
        existing = set()
        for i in range(0, len(results), 50):
            chunk = results[i:i + 50]
            pairs = [(f["osm_id"], f["osm_type"]) for f in chunk]
            stmt = select(Organization.osm_id, Organization.osm_type).where(
                tuple_(Organization.osm_id, Organization.osm_type).in_(pairs)
            )
            for osm_id, osm_type in (await db.execute(stmt)).all():
                existing.add((osm_id, osm_type))
        for fac in results:
            fac["already_imported"] = (fac["osm_id"], fac["osm_type"]) in existing

    # keep only facilities within the requested radius, nearest first
    clat, clng, radius_km = body.lat, body.lng, body.radius_km
    results = [
        f for f in results
        if _haversine_km(clat, clng, f["lat"] or clat, f["lng"] or clng) <= radius_km
    ]
    results.sort(key=lambda f: _haversine_km(clat, clng, f["lat"] or clat, f["lng"] or clng))
    for f in results:
        f["distance_km"] = round(
            _haversine_km(clat, clng, f["lat"] or clat, f["lng"] or clng), 2
        )
    return {"facilities": results[:MAX_IMPORT_RESULTS]}


# ── import a selected facility (source='healthsites.io') ─────

@router.post("/import")
async def import_healthsite(
    body: ImportBody,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Import a single facility from healthsites.io as a new organization."""
    fac = body.facility
    if not fac.osm_id or not fac.osm_type:
        raise HTTPException(status_code=400, detail="osm_id and osm_type are required")

    exists = await db.execute(
        select(Organization).where(
            Organization.osm_id == fac.osm_id,
            Organization.osm_type == fac.osm_type,
        )
    )
    if exists.scalar_one_or_none():
        return {"added": 0, "skipped": 1, "message": "Already imported"}

    org = Organization(
        name=fac.name.strip(),
        country=(fac.country or "").strip(),
        type=fac.type or "clinic",
        latitude=fac.lat,
        longitude=fac.lng,
        osm_id=fac.osm_id,
        osm_type=fac.osm_type,
        source="healthsites.io",
    )
    db.add(org)
    try:
        await db.flush()
        db.add(OrgUser(
            profile_id=profile.id,
            organization_id=org.id,
            role="admin",
        ))
        await db.commit()
    except Exception as exc:
        await db.rollback()
        if "uq_organizations_osm" in str(exc):
            raise HTTPException(status_code=409, detail="This facility was already imported (duplicate OSM id)")
        raise
    await db.refresh(org)
    return {"added": 1, "skipped": 0, "id": str(org.id), "name": org.name}


# ── edit / delete ────────────────────────────────────────────

@router.patch("/{org_id}")
async def update_healthsite(
    org_id: _uuid.UUID,
    body: HealthsiteUpdate,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = profile.get_role_for_org(org_id)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only org admins can manage healthsites")
    if body.name is not None:
        org.name = body.name
    if body.country is not None:
        org.country = body.country
    if body.latitude is not None:
        org.latitude = body.latitude
    if body.longitude is not None:
        org.longitude = body.longitude
    await db.commit()
    await db.refresh(org)
    return _org_dict(org)


@router.delete("/{org_id}")
async def delete_healthsite(
    org_id: _uuid.UUID,
    profile: Profile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = profile.get_role_for_org(org_id)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only org admins can manage healthsites")
    if org.source != "healthsites.io":
        raise HTTPException(status_code=400, detail="Only imported healthsites can be deleted from here")

    members = await db.execute(select(OrgUser).where(OrgUser.organization_id == org_id))
    if members.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This healthsite has members and cannot be deleted")
    devices = await db.execute(select(Device.id).where(Device.organization_id == org_id))
    if devices.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This healthsite has devices and cannot be deleted")

    await db.delete(org)
    await db.commit()
    return {"message": "Healthsite deleted"}