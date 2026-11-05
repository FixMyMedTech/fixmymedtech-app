from urllib.parse import urlencode

import httpx

from config.api import _get, _post, _delete, _raise, API_URL


# ── Documents ────────────────────────────────────────────────
async def search_library(q: str = "", type: str = ""):
    params = {k: v for k, v in (("q", q.strip()), ("type", type)) if v}
    return await _get("/api/documents/" + (f"?{urlencode(params)}" if params else ""))

async def search_ifixit(q: str):
    return await _get(f"/api/documents/ifixit/search?{urlencode({'q': q})}")

async def device_documents(device_id: str):
    return await _get(f"/api/devices/{device_id}/documents")

async def attach_ifixit(token: str, device_id: str, page: str, document_id: int):
    return await _post(f"/api/devices/{device_id}/documents/ifixit",
                       {"ifixit_page": page, "ifixit_document_id": document_id}, token)

async def detach(token: str, device_id: str, document_id: str):
    return await _delete(f"/api/devices/{device_id}/documents/{document_id}", token)

async def upload(token: str, device_id: str, filename: str, content: bytes,
                 title: str, type: str, language: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
        r = await client.post(
            f"{API_URL}/api/devices/{device_id}/documents/upload",
            data={"title": title, "type": type, "language": language},
            files={"file": (filename or "document.pdf", content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        _raise(r)
        return r.json()

async def get_file(document_id: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
        r = await client.get(f"{API_URL}/api/documents/{document_id}/file")
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "application/pdf"), r.headers.get("content-disposition")
