# api.py — HTTP client that calls the FastAPI backend

import httpx
import os

API_URL = os.getenv("API_URL", "http://localhost:8888")


async def _get(path: str, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}{path}", headers=headers)
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}{path}", json=data, headers=headers)
        r.raise_for_status()
        return r.json()


async def _patch(path: str, data: dict, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        r = await client.patch(f"{API_URL}{path}", json=data, headers=headers)
        r.raise_for_status()
        return r.json()