# api.py — HTTP client that calls the FastAPI backend

import httpx
import os
from contextvars import ContextVar

API_URL = os.getenv("API_URL", "http://localhost:8888")

# Set per request by UserContextMiddleware (frontend/main.py). A 401 on a call
# that carried a token marks it, so the middleware can end the session even
# when the page itself swallowed the error and rendered an empty page.
token_rejected: ContextVar[dict | None] = ContextVar("token_rejected", default=None)
# Set when the API answers 403 community_access_pending: the session still
# thinks this account is a member, but it is (again) a community applicant.
access_pending: ContextVar[dict | None] = ContextVar("access_pending", default=None)


def _raise(r: httpx.Response):
    if r.status_code < 400:
        return
    if r.status_code == 401 and r.request.headers.get("authorization"):
        flag = token_rejected.get()
        if flag is not None:
            flag["rejected"] = True
    try:
        detail = r.json().get("detail") or r.text
    except Exception:
        detail = r.text
    if r.status_code == 403 and detail == "community_access_pending":
        flag = access_pending.get()
        if flag is not None:
            flag["pending"] = True
    if isinstance(detail, list):
        detail = "; ".join(str(d.get("msg", d)) for d in detail if isinstance(d, dict))
    raise httpx.HTTPStatusError(detail, request=r.request, response=r)


async def _get(path: str, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}{path}", headers=headers)
        _raise(r)
        return r.json()


async def _post(path: str, data: dict, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}{path}", json=data, headers=headers)
        _raise(r)
        return r.json()


async def _patch(path: str, data: dict, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.patch(f"{API_URL}{path}", json=data, headers=headers)
        _raise(r)
        return r.json()


async def _delete(path: str, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{API_URL}{path}", headers=headers)
        _raise(r)
        if r.status_code == 204:
            return {}
        return r.json()