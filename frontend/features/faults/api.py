from config.api import _get, _post, _patch, API_URL
import httpx


# ── Faults ───────────────────────────────────────────────────
async def submit_fault_public(data: dict, token: str = None):
    return await _post("/api/faults/public", data, token)

async def upload_fault_photo(token: str, fault_id: str, filename: str, content: bytes, content_type: str = None):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"photo": (filename, content, content_type or "application/octet-stream")}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL}/api/faults/{fault_id}/photo",
            files=files, headers=headers,
        )
        r.raise_for_status()
        return r.json()

async def get_fault_photo(token: str, fault_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/faults/{fault_id}/photo", headers=headers)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")

async def get_fault_photo_public(fault_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/faults/public/{fault_id}/photo")
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/jpeg")

async def get_fault_assignees(token: str, device_id: str):
    return await _get(f"/api/faults/assignees/{device_id}", token)

async def get_fault(token: str, fault_id: str):
    return await _get(f"/api/faults/{fault_id}", token)

async def list_faults(token: str, status: str = None):
    path = "/api/faults/" + (f"?status={status}" if status else "")
    return await _get(path, token)


async def list_maintained_faults(token: str, status: str = None):
    """Faults on devices my organizations MAINTAIN (not the ones they own)."""
    path = "/api/faults/maintained" + (f"?status={status}" if status else "")
    return await _get(path, token)


async def update_fault(token: str, fault_id: str, data: dict):
    return await _patch(f"/api/faults/{fault_id}", data, token)


# ── Workflow steps ───────────────────────────────────────────
# Each step has its own endpoint because each one has its own authorizer:
# assign -> maintenance-org admin; diagnosis/resolve -> the assignee;
# approval -> the healthsite admin (maintenance admin when there is no healthsite).

async def assign_fault(token: str, fault_id: str, assigned_to: str):
    return await _patch(f"/api/faults/{fault_id}/assign", {"assigned_to": assigned_to}, token)


async def start_fault(token: str, fault_id: str):
    return await _patch(f"/api/faults/{fault_id}/start", {}, token)


async def submit_diagnosis(token: str, fault_id: str, diagnosis: str,
                           quote_amount=None, quote_notes: str = None):
    return await _patch(f"/api/faults/{fault_id}/diagnosis", {
        "diagnosis": diagnosis,
        "quote_amount": quote_amount,
        "quote_notes": quote_notes,
    }, token)


async def review_approval(token: str, fault_id: str, approved: bool, comment: str = None):
    return await _patch(f"/api/faults/{fault_id}/approval", {
        "approved": approved,
        "comment": comment,
    }, token)


async def resolve_fault(token: str, fault_id: str, resolution_notes: str, final_price=None):
    return await _patch(f"/api/faults/{fault_id}/resolve", {
        "resolution_notes": resolution_notes,
        "final_price": final_price,
    }, token)


async def get_fault_public(fault_id: str):
    return await _get(f"/api/faults/public/{fault_id}")
