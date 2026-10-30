# routers/documents.py — the document library (manuals and guides).
#
# Two routers:
#   router         mounted at /api/documents   library search, iFixit search, files
#   device_router  mounted at /api/devices     a device's documents
#
# Reading is public (documents show on the QR page and the public library).
# Attaching, uploading and removing need a logged-in user, any logged-in user.
#
# iFixit documents are stored as LINKS only (url + iFixit ids), once per iFixit
# document, and their metadata always comes from iFixit itself, never from the
# browser. Uploaded PDFs go to MinIO and start with contribution_status
# 'pending': a platform superuser decides later whether to send them to iFixit.
#
# Responses are built by hand from columns (see the note in
# routers/fault_reports.py about Profile.user and hashed_password).

import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File as FileParam, Form, HTTPException, UploadFile
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import config.ifixit as ifixit
from config.db_config import get_db
from config.storage import get_file, upload_file
from config.users import current_active_user
from models.models import DOCUMENT_TYPES, Device, DeviceDocument, Document, User

router = APIRouter()
device_router = APIRouter()

LANGUAGES = ("en", "es", "fr", "pt", "de", "it", "other")
MAX_UPLOAD_MB = int(os.getenv("DOCUMENT_MAX_MB") or 50)
TITLE_MAX = 200


def doc_payload(d: Document) -> dict:
    """Public view of a library document. Uploads are served by
    /api/documents/{id}/file; iFixit documents open on iFixit."""
    return {
        "id": str(d.id),
        "title": d.title,
        "type": d.type,
        "language": d.language,
        "source": d.source,
        "url": d.url if d.source == "ifixit" else f"/documents/{d.id}/file",
        "size_kb": d.size_kb,
        "pages": d.pages,
        "thumbnail_url": d.thumbnail_url,
        "manufacturer": d.manufacturer,
        "model": d.model,
        "ifixit_page": d.ifixit_page,
        "contribution_status": d.contribution_status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


async def device_documents(db: AsyncSession, device_id) -> list[dict]:
    """A device's documents, newest link first (also used by routers/devices.py)."""
    rows = (await db.execute(
        select(Document, DeviceDocument.added_by)
        .join(DeviceDocument, DeviceDocument.document_id == Document.id)
        .where(DeviceDocument.device_id == device_id)
        .order_by(DeviceDocument.created_at.desc())
    )).all()
    return [{**doc_payload(d), "added_by": str(added_by) if added_by else None} for d, added_by in rows]


async def _load_device(db: AsyncSession, device_id: UUID) -> Device:
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


async def _link(db: AsyncSession, device_id, document_id, user_id) -> bool:
    """Link a document to a device. False if it was already linked."""
    exists = (await db.execute(select(DeviceDocument).where(
        DeviceDocument.device_id == device_id, DeviceDocument.document_id == document_id
    ))).scalar_one_or_none()
    if exists:
        return False
    db.add(DeviceDocument(device_id=device_id, document_id=document_id, added_by=user_id))
    return True


# ── library ──────────────────────────────────────────────────────────────────

@router.get("/")
async def search_library(q: str = "", type: str = "", limit: int = 50,
                         db: AsyncSession = Depends(get_db)):
    """FixMyMedTech's library: every document linked or uploaded here."""
    limit = max(1, min(limit, 100))
    used_by = (select(DeviceDocument.document_id, func.count().label("devices"))
               .group_by(DeviceDocument.document_id).subquery())
    stmt = (select(Document, func.coalesce(used_by.c.devices, 0))
            .outerjoin(used_by, used_by.c.document_id == Document.id))
    for word in q.split()[:6]:
        like = f"%{word}%"
        stmt = stmt.where(or_(Document.title.ilike(like), Document.manufacturer.ilike(like),
                              Document.model.ilike(like), Document.ifixit_page.ilike(like)))
    if type in DOCUMENT_TYPES:
        stmt = stmt.where(Document.type == type)
    rows = (await db.execute(stmt.order_by(Document.created_at.desc()).limit(limit))).all()
    return [{**doc_payload(d), "devices": n} for d, n in rows]


@router.get("/ifixit/search")
async def search_ifixit(q: str):
    """iFixit device pages matching q, each with its documents."""
    try:
        return await ifixit.search(q)
    except Exception:
        raise HTTPException(status_code=502, detail="iFixit is not reachable right now")


@router.get("/{document_id}/file")
async def get_document_file(document_id: UUID, db: AsyncSession = Depends(get_db)):
    d = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
    if not d or d.source != "upload" or not d.storage_key:
        raise HTTPException(status_code=404, detail="No file")
    obj = await get_file(d.storage_key)
    if obj is None:
        raise HTTPException(status_code=404, detail="File not found in storage")
    content, ctype = obj
    safe = "".join(c for c in d.title if c.isalnum() or c in " -_.")[:80].strip() or "document"
    return FastAPIResponse(content=content, media_type=ctype or "application/pdf",
                           headers={"Content-Disposition": f'inline; filename="{safe}.pdf"'})


# ── a device's documents ─────────────────────────────────────────────────────

class IfixitAttach(BaseModel):
    ifixit_page: str
    ifixit_document_id: int
    type: Optional[str] = None


@device_router.get("/{device_id}/documents")
async def list_device_documents(device_id: UUID, db: AsyncSession = Depends(get_db)):
    await _load_device(db, device_id)
    return await device_documents(db, device_id)


@device_router.post("/{device_id}/documents/ifixit")
async def attach_ifixit_document(device_id: UUID, body: IfixitAttach,
                                 user: User = Depends(current_active_user),
                                 db: AsyncSession = Depends(get_db)):
    device = await _load_device(db, device_id)
    doc = (await db.execute(select(Document).where(
        Document.ifixit_document_id == body.ifixit_document_id))).scalar_one_or_none()
    if doc is None:
        try:
            meta = await ifixit.find_document(body.ifixit_page, body.ifixit_document_id)
        except Exception:
            raise HTTPException(status_code=502, detail="iFixit is not reachable right now")
        if meta is None:
            raise HTTPException(status_code=404, detail="Document not found on iFixit")
        doc = Document(
            id=uuid.uuid4(), source="ifixit",
            title=meta["title"][:TITLE_MAX],
            type=body.type if body.type in DOCUMENT_TYPES else meta["type"],
            language="en", url=meta["url"], size_kb=meta["size_kb"], pages=meta["pages"],
            thumbnail_url=meta["thumbnail_url"], ifixit_document_id=meta["ifixit_document_id"],
            ifixit_guid=meta["ifixit_guid"], ifixit_page=meta["ifixit_page"],
            manufacturer=device.manufacturer, model=device.model,
        )
        db.add(doc)
        try:
            await db.flush()
        except IntegrityError:
            # Someone stored the same iFixit document a moment ago: reuse it.
            await db.rollback()
            doc = (await db.execute(select(Document).where(
                Document.ifixit_document_id == body.ifixit_document_id))).scalar_one()
    linked = await _link(db, device_id, doc.id, user.id)
    await db.commit()
    return {**doc_payload(doc), "linked": linked}


@device_router.post("/{device_id}/documents/upload")
async def upload_device_document(
    device_id: UUID,
    file: UploadFile = FileParam(...),
    title: str = Form(...),
    type: str = Form(...),
    language: str = Form("en"),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    device = await _load_device(db, device_id)
    title = " ".join(title.split())[:TITLE_MAX]
    if not title:
        raise HTTPException(status_code=400, detail="A title is required")
    if type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unknown document type")
    content = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"The file is larger than {MAX_UPLOAD_MB} MB")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Only PDF files can be uploaded")

    doc_id = uuid.uuid4()
    key = await upload_file("documents", str(doc_id), "document.pdf", content, "application/pdf")
    doc = Document(
        id=doc_id, source="upload", title=title, type=type,
        language=language if language in LANGUAGES else "other",
        storage_key=key, size_kb=round(len(content) / 1024),
        manufacturer=device.manufacturer, model=device.model,
        uploaded_by=user.id, contribution_status="pending",
    )
    db.add(doc)
    await db.flush()
    await _link(db, device_id, doc.id, user.id)
    await db.commit()
    return doc_payload(doc)


@device_router.post("/{device_id}/documents/{document_id}")
async def attach_library_document(device_id: UUID, document_id: UUID,
                                  user: User = Depends(current_active_user),
                                  db: AsyncSession = Depends(get_db)):
    """Attach a document that is already in the library."""
    await _load_device(db, device_id)
    doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    linked = await _link(db, device_id, doc.id, user.id)
    await db.commit()
    return {**doc_payload(doc), "linked": linked}


@device_router.delete("/{device_id}/documents/{document_id}")
async def detach_document(device_id: UUID, document_id: UUID,
                          user: User = Depends(current_active_user),
                          db: AsyncSession = Depends(get_db)):
    """Remove a document from a device. The document stays in the library."""
    link = (await db.execute(select(DeviceDocument).where(
        DeviceDocument.device_id == device_id, DeviceDocument.document_id == document_id
    ))).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="That document is not attached to this device")
    await db.delete(link)
    await db.commit()
    return {"status": "removed"}
