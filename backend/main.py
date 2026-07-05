# ============================================================
# MedTrack QR — FastAPI Backend
# ============================================================
# Install: pip install fastapi uvicorn supabase python-dotenv pydantic
# Run:     uvicorn main:app --reload
# ============================================================

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from starlette.responses import RedirectResponse
from fastapi import FastAPI, Request
from fastapi.responses import Response
import httpx

from models import models
from config.supabase_config import supa_client, engine, AsyncSessionLocal, Base
from routers import devices, fault_reports, dashboard, auth, organizations
from config.supabase_config import supa_client

load_dotenv()

# # create table in the database
# models.Base.metadata.create_all(bind=engine)
# models.automap_base()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.supabase = supa_client
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: models.Base.metadata.create_all(
                bind=sync_conn,
            )
        )
        models.automap_base()
    yield

app = FastAPI(
    title="FixMyMedTech API",
    description="Medical equipment management for LMICs",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False, 
)

# create table in the database
# models.Base.metadata.create_all(bind=engine)
# models.automap_base()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",    tags=["auth"])
app.include_router(devices.router,      prefix="/api/devices", tags=["devices"])
app.include_router(fault_reports.router,prefix="/api/faults",  tags=["faults"])
app.include_router(dashboard.router,    prefix="/api/dashboard",tags=["dashboard"])
app.include_router(organizations.router,    prefix="/api/organizations",tags=["organizations"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "medtrack-api"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    url = f"http://localhost:5001/{path}"
    headers = dict(request.headers)

    data = await request.body()

    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            response = await client.get(url, headers=headers)
        elif request.method == "POST":
            response = await client.post(url, headers=headers, content=data)
        elif request.method == "PUT":
            response = await client.put(url, headers=headers, content=data)
        elif request.method == "DELETE":
            response = await client.delete(url, headers=headers, content=data)

    return Response(        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )

@app.get('/')
def default_route():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)