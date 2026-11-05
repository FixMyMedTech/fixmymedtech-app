"""Read-only client for the public iFixit API (https://www.ifixit.com/api/2.0).

On iFixit, manuals and guides are PDFs attached to a device page ("wiki" in
the CATEGORY namespace, e.g. "Mindray Accutorr 3"). Searching by manufacturer
and model finds those pages; each page lists its documents.

Reading needs no account. Results are cached in memory for a day so repeated
searches (registration, device page, library) don't hit iFixit every time.

Configuration (environment variables):

* ``IFIXIT_API_URL`` — defaults to https://www.ifixit.com/api/2.0.
"""

import asyncio
import os
import re
import time
from typing import Optional
from urllib.parse import quote

import httpx

API_URL = os.getenv("IFIXIT_API_URL", "https://www.ifixit.com/api/2.0").rstrip("/")
SITE_URL = "https://www.ifixit.com"
CACHE_TTL = 24 * 3600
MAX_PAGES = 6          # device pages fetched per search
_cache: dict[str, tuple[float, object]] = {}


async def _get_json(path: str, params: Optional[dict] = None):
    key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0),
                                 headers={"User-Agent": "FixMyMedTech (+https://fixmymedtech.org)"}) as client:
        r = await client.get(API_URL + path, params=params)
    if r.status_code == 404:
        data = None
    else:
        r.raise_for_status()
        data = r.json()
    if len(_cache) > 2000:
        _cache.clear()
    _cache[key] = (time.time(), data)
    return data


def guess_type(title: str) -> str:
    """iFixit documents have no type; guess one from the title."""
    t = (title or "").lower()
    if re.search(r"service|repair|technical|maintenance|troubleshoot", t):
        return "service_manual"
    if re.search(r"schematic|diagram|circuit|wiring|exploded|parts? list", t):
        return "diagram"
    if re.search(r"quick|checklist|reference card|cheat", t):
        return "quick_guide"
    if re.search(r"user|operat|instruction|owner|ifu\b|manual", t):
        return "user_manual"
    return "general_guide"


def _clean_title(title: str) -> str:
    """"Mindray_Accutorr_3_Manual.pdf.pdf" → "Mindray Accutorr 3 Manual"."""
    t = (title or "").strip()
    while re.search(r"\.(pdf|txt|md)$", t, flags=re.I):
        t = re.sub(r"\.(pdf|txt|md)$", "", t, flags=re.I)
    return " ".join(t.replace("_", " ").split())


def _doc(page_title: str, d: dict) -> dict:
    image = d.get("image") or {}
    url = d.get("url") or ""
    return {
        "ifixit_document_id": int(d["documentid"]),
        "ifixit_guid": d.get("guid"),
        "ifixit_page": page_title,
        "title": _clean_title(d.get("title") or d.get("filename") or "Document"),
        "type": guess_type(d.get("title") or d.get("filename") or ""),
        "url": url if url.startswith("http") else SITE_URL + url,
        "size_kb": round((d.get("size") or 0) / 1024) or None,
        "pages": d.get("pages"),
        "thumbnail_url": image.get("thumbnail") or image.get("mini"),
        "extension": d.get("document_extension"),
    }


async def get_page(page_title: str) -> Optional[dict]:
    """A device page with its documents, or None if it doesn't exist."""
    w = await _get_json(f"/wikis/CATEGORY/{quote(page_title.replace(' ', '_'), safe='')}")
    if not w:
        return None
    title = w.get("title") or page_title
    return {
        "title": title,
        "url": f"{SITE_URL}/Device/{quote(title.replace(' ', '_'))}",
        "image": ((w.get("image") or {}).get("thumbnail")),
        "documents": [_doc(title, d) for d in (w.get("documents") or []) if d.get("documentid")],
    }


async def search(query: str) -> list[dict]:
    """Device pages matching ``query`` (e.g. "Mindray Accutorr"), each with
    its documents. Pages without documents are left out."""
    query = " ".join((query or "").split())[:100]
    if len(query) < 2:
        return []
    res = await _get_json(f"/search/{quote(query, safe='')}", {"limit": 20})
    titles = [x["title"] for x in (res or {}).get("results", [])
              if x.get("dataType") == "wiki" and x.get("namespace") == "CATEGORY" and x.get("title")]
    pages = await asyncio.gather(*(get_page(t) for t in titles[:MAX_PAGES]), return_exceptions=True)
    return [p for p in pages if isinstance(p, dict) and p["documents"]]


async def find_document(page_title: str, document_id: int) -> Optional[dict]:
    """One document's metadata, looked up on iFixit itself (never trusted
    from the browser)."""
    page = await get_page(page_title)
    for d in (page or {}).get("documents", []):
        if d["ifixit_document_id"] == document_id:
            return d
    return None
