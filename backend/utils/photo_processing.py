"""Photo preprocessing (background cleanup onto a pure white background).

Turns a raw device photo into a clean, object-on-pure-white-background
catalogue-style image (see resources/INSPIRATION/INSPIRATION-konglodigital.md).

Providers, in order of preference:
  1. Gemini image-edit API ("Nano Banana") — if ``GEMINI_API_KEY`` is set.
  2. rembg (local background removal + white fill) — default, no API key.

This module provides two kinds of processing:

* ``compress_device_photo`` — downscale/re-encode before storing (called
  synchronously in the upload request, cheap).
* ``process_photo_to_white`` — background cleanup onto a pure white
  background (called from a background task so registration never waits).

Neither ever blocks the flow: failures keep the raw bytes.
"""

import asyncio
import base64
import io
import logging
import os

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("storage.photos")

AUTO_PROCESS_PHOTO = os.getenv("AUTO_PROCESS_PHOTO", "on").lower() != "off"
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_PHOTO_MODEL = os.getenv("GEMINI_PHOTO_MODEL", "gemini-2.5-flash-image")

# Compression defaults — keep stored photos small while staying sharp enough
# for catalogue / fault-review use.
PHOTO_MAX_DIMENSION = int(os.getenv("PHOTO_MAX_DIMENSION", "1600"))
PHOTO_JPEG_QUALITY  = int(os.getenv("PHOTO_JPEG_QUALITY", "85"))

_rembg_session   = None
_rembg_available = None


def _compress_photo(content: bytes) -> tuple[bytes, str, str] | None:
    """Downscale + re-encode as an optimized progressive JPEG.

    Corrects EXIF orientation, composites transparency onto white, and
    returns ``(bytes, "image/jpeg", "device_photo.jpg")``. Returns ``None``
    when the input isn't a decodable image (caller keeps raw bytes).
    """
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(content))
        img.load()
        img = ImageOps.exif_transpose(img)

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            white = Image.new("RGB", img.size, (255, 255, 255))
            white.paste(img, mask=img.split()[3])
            img = white
        else:
            img = img.convert("RGB")

        img.thumbnail((PHOTO_MAX_DIMENSION, PHOTO_MAX_DIMENSION), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=PHOTO_JPEG_QUALITY, optimize=True, progressive=True)
        return buf.getvalue(), "image/jpeg", "device_photo.jpg"
    except Exception as e:  # noqa: BLE001
        log.warning("photo compression failed (%s); storing original bytes", e)
        return None


async def compress_device_photo(
    content: bytes,
    mime_type: str = "image/jpeg",
    filename: str = "device_photo.jpg",
) -> tuple[bytes, str, str]:
    """Return a compressed copy of the photo, or the input unchanged."""
    out = await asyncio.to_thread(_compress_photo, content)
    if out:
        return out
    return content, mime_type, filename


def _get_rembg_session():
    """Lazily initialise the rembg background-removal session (model ~176 MB)."""
    global _rembg_session, _rembg_available
    if _rembg_available is False:
        return None
    if _rembg_session is None:
        try:
            from rembg import new_session
            _rembg_session = new_session("u2net")
            _rembg_available = True
        except Exception as e:  # noqa: BLE001
            _rembg_available = False
            log.warning("rembg unavailable (%s); photos stored unprocessed", e)
            return None
    return _rembg_session


async def _white_bg_via_gemini(content: bytes, mime_type: str) -> bytes | None:
    """Ask Google's Gemini image-edit model ("Nano Banana") to whiten the background."""
    import httpx

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_PHOTO_MODEL}:generateContent"
    )
    payload = {
        "contents": [{
            "parts": [
                {"text": "Remove the background of this image completely and "
                         "replace it with a clean pure-white background "
                         "(RGB 255,255,255). Keep the main subject untouched "
                         "and sharp."},
                {"inlineData": {
                    "mimeType": mime_type or "image/jpeg",
                    "data": base64.b64encode(content).decode("ascii"),
                }},
            ]
        }]
    }
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, params={"key": GEMINI_API_KEY}, json=payload)
        r.raise_for_status()
        resp = r.json()

    for part in resp.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        data = part.get("inlineData") or {}
        if data.get("data"):
            return base64.b64decode(data["data"])
    return None


def _white_bg_via_rembg(content: bytes) -> bytes | None:
    """Local background removal (rembg/u2net) composited onto pure white."""
    session = _get_rembg_session()
    if session is None:
        return None
    try:
        from rembg import remove
        from PIL import Image

        img = Image.open(io.BytesIO(content))
        img.load()
        if img.mode != "RGB":
            img = img.convert("RGB")

        cutout = remove(img, session=session)
        if isinstance(cutout, bytes):
            cutout = Image.open(io.BytesIO(cutout))
        cutout = cutout.convert("RGBA")

        white = Image.new("RGBA", cutout.size, (255, 255, 255, 255))
        composite = Image.alpha_composite(white, cutout).convert("RGB")

        buf = io.BytesIO()
        composite.save(buf, "JPEG", quality=PHOTO_JPEG_QUALITY, optimize=True, progressive=True)
        return buf.getvalue()
    except Exception as e:  # noqa: BLE001
        log.warning("photo background cleanup failed (%s); storing original", e)
        return None


async def process_photo_to_white(
    content: bytes,
    mime_type: str = "image/jpeg",
    filename: str = "device_photo.jpg",
) -> tuple[bytes, str, str] | None:
    """Return ``(bytes, content_type, filename)`` of the cleaned photo.

    Returns ``None`` when processing is disabled or fails — callers keep
    serving the original image. Never raises.
    """
    if not AUTO_PROCESS_PHOTO:
        return None

    if GEMINI_API_KEY:
        try:
            out = await _white_bg_via_gemini(content, mime_type)
            if out:
                return out, "image/jpeg", "device_photo.jpg"
            log.warning("Gemini returned no image; falling back to rembg")
        except Exception as e:  # noqa: BLE001
            log.warning("Gemini photo cleanup failed (%s); falling back to rembg", e)

    out = await asyncio.to_thread(_white_bg_via_rembg, content)
    if out:
        return out, "image/jpeg", "device_photo.jpg"
    return None