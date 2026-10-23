from config.api import _raise, API_URL
import httpx


# ── Feedback ─────────────────────────────────────────────────
async def submit_feedback(data: dict, token: str = None, screenshot: tuple = None):
    """Send a feedback/issue report. ``screenshot`` is an optional
    ``(filename, bytes, content_type)``. Works with or without a token."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    files = {"screenshot": screenshot} if screenshot else None
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}/api/feedback/", data=data, files=files, headers=headers)
        _raise(r)
        return r.json()
