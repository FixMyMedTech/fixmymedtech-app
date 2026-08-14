# api.py — HTTP client that calls the FastAPI backend

import httpx
import os

API_URL = os.getenv("API_URL", "http://localhost:8888")


def _raise(r: httpx.Response):
    if r.status_code < 400:
        return
    try:
        detail = r.json().get("detail") or r.text
    except Exception:
        detail = r.text
    if isinstance(detail, list):
        detail = "; ".join(str(d.get("msg", d)) for d in detail if isinstance(d, dict))
    raise RuntimeError(detail)


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