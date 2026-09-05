# routers/admin_email.py — Admin email actions (invite + verify)

import os
import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

from admin_auth import _sync_engine, require_superuser
from sqlalchemy import text

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8888")


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: str


# ── Invite form ───────────────────────────────────────────────────────────────

@router.get("/invite", response_class=HTMLResponse)
async def invite_form(request: Request):
    await require_superuser(request)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Invite User — FixMyMedTech Admin</title>
<style>
  body{font-family:system-ui,-apple-system,sans-serif;max-width:560px;margin:40px auto;padding:0 20px;color:#1a1a1a}
  h1{font-size:1.5rem;margin-bottom:4px}
  .sub{color:#666;margin-top:0;margin-bottom:24px}
  label{display:block;font-weight:600;margin-bottom:4px}
  input[type=text],input[type=email]{width:100%;padding:10px 12px;border:1px solid #ccc;border-radius:6px;font-size:1rem;box-sizing:border-box}
  .row{margin-bottom:16px}
  button{background:#2563eb;color:#fff;border:none;padding:12px 24px;border-radius:6px;font-size:1rem;cursor:pointer}
  button:hover{background:#1d4ed8}
  .note{background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:12px;margin-top:24px;font-size:.9rem;color:#0369a1}
  a{color:#2563eb}
  .flash{background:#dcfce7;border:1px solid #86efac;border-radius:6px;padding:12px;margin-bottom:16px;color:#166534}
  .flash.err{background:#fef2f2;border-color:#fca5a5;color:#991b1b}
</style>
</head>
<body>
<h1>Invite a User</h1>
<p class="sub">Send a verification email so they can set their password and start using FixMyMedTech.</p>

<div id="flash"></div>

<form id="f" method="post" action="/admin-panel/invite">
  <div class="row">
    <label for="email">Email address</label>
    <input type="email" id="email" name="email" required placeholder="user@hospital.org">
  </div>
  <div class="row">
    <label for="full_name">Full name</label>
    <input type="text" id="full_name" name="full_name" required placeholder="Dr. Jane Smith">
  </div>
  <button type="submit">Send Invitation</button>
</form>

<div class="note">
  <strong>How it works:</strong> An account is created (or found) and a verification email
  is sent with a link to set their password. You can also resend verification from the
  <a href="/admin/user/list">Users list</a>.
</div>

<script>
document.getElementById("f").addEventListener("submit", async function(e){
  e.preventDefault();
  const fd = new FormData(this);
  const r = await fetch(this.action, {method:"POST", body:fd, redirect:"manual"});
  if(r.status===303||r.status===302){
    document.getElementById("flash").innerHTML='<div class="flash">Invitation sent!</div>';
    this.reset();
  } else {
    const j = await r.json().catch(()=>({detail:"Error"}));
    document.getElementById("flash").innerHTML='<div class="flash err">'+j.detail+'</div>';
  }
});
</script>
</body>
</html>"""


# ── Send invitation ───────────────────────────────────────────────────────────

@router.post("/invite")
async def send_invite(request: Request):
    await require_superuser(request)

    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    full_name = (form.get("full_name") or "").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")

    # Find or create user
    with _sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, is_verified FROM fixmymedtech.users WHERE email = :e"),
            {"e": email},
        ).mappings().first()

        if row:
            user_id = row["id"]
            already_verified = row["is_verified"]
        else:
            # Create user with random password (they'll set it via verification)
            from pwdlib import PasswordHash
            from pwdlib.hashers.bcrypt import BcryptHasher
            hasher = PasswordHash(hashers=[BcryptHasher()])
            pw = hasher.hash(uuid.uuid4().hex[:16])
            user_id = uuid.uuid4()

            conn.execute(
                text("INSERT INTO fixmymedtech.users "
                     "(id, email, full_name, hashed_password, is_active, is_superuser, is_verified) "
                     "VALUES (:id, :email, :name, :pw, true, false, false)"),
                {"id": user_id, "email": email, "name": full_name, "pw": pw},
            )
            # Create profile + default org
            username = email.split("@")[0].replace(".", "_")
            conn.execute(
                text("INSERT INTO fixmymedtech.profiles (id, username, full_name) "
                     "VALUES (:id, :u, :n)"),
                {"id": user_id, "u": username, "n": full_name},
            )
            org_id = uuid.uuid4()
            conn.execute(
                text("INSERT INTO fixmymedtech.organizations (id, name, country, type) "
                     "VALUES (:id, :n, '', 'hospital')"),
                {"id": org_id, "n": full_name},
            )
            conn.execute(
                text("INSERT INTO fixmymedtech.org_users (id, profile_id, organization_id, role) "
                     "VALUES (:id, :pid, :oid, 'admin')"),
                {"id": uuid.uuid4(), "pid": user_id, "oid": org_id},
            )
            already_verified = False

    # Generate verification token and send email
    from fastapi_users.jwt import generate_jwt
    token = generate_jwt(
        {"sub": str(user_id), "email": email, "aud": "fastapi-users:verify"},
        os.getenv("AUTH_JWT_SECRET", "dev-local-jwt-secret-change-me"),
        86400,  # 24 hours
    )

    from config.email import send_verification_email
    base_url = os.getenv("FRONTEND_URL", "http://localhost:8888")
    await send_verification_email(email, token, base_url)

    # Return JSON for AJAX, or redirect for form submit
    accept = request.headers.get("accept", "")
    if "json" in accept:
        return {"message": f"Invitation sent to {email}"}
    return RedirectResponse("/admin-panel/invite", status_code=303)


# ── Resend verification to existing user ──────────────────────────────────────

@router.post("/send-verification/{user_id}")
async def resend_verification(user_id: str, request: Request):
    await require_superuser(request)

    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    with _sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT email, full_name, is_verified, is_active "
                 "FROM fixmymedtech.users WHERE id = :id"),
            {"id": uid},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    if row["is_verified"]:
        raise HTTPException(status_code=400, detail="User is already verified")
    if not row["is_active"]:
        raise HTTPException(status_code=400, detail="User account is inactive")

    from fastapi_users.jwt import generate_jwt
    token = generate_jwt(
        {"sub": str(uid), "email": row["email"], "aud": "fastapi-users:verify"},
        os.getenv("AUTH_JWT_SECRET", "dev-local-jwt-secret-change-me"),
        86400,
    )

    from config.email import send_verification_email
    base_url = os.getenv("FRONTEND_URL", "http://localhost:8888")
    await send_verification_email(row["email"], token, base_url)

    accept = request.headers.get("accept", "")
    if "json" in accept:
        return {"message": f"Verification email sent to {row['email']}"}
    return RedirectResponse(f"/admin/user/details/{uid}", status_code=303)


# ── Send password reset from admin ────────────────────────────────────────────

@router.post("/send-reset/{user_id}")
async def send_reset(user_id: str, request: Request):
    await require_superuser(request)

    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    with _sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT email, full_name, is_active, hashed_password "
                 "FROM fixmymedtech.users WHERE id = :id"),
            {"id": uid},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    if not row["is_active"]:
        raise HTTPException(status_code=400, detail="User account is inactive")

    from fastapi_users.jwt import generate_jwt
    from pwdlib import PasswordHash
    from pwdlib.hashers.bcrypt import BcryptHasher
    token = generate_jwt(
        {
            "sub": str(uid),
            "email": row["email"],
            "password_fgpt": PasswordHash(hashers=[BcryptHasher()]).hash(row["hashed_password"]),
            "aud": "fastapi-users:reset",
        },
        os.getenv("AUTH_JWT_SECRET", "dev-local-jwt-secret-change-me"),
        3600,  # 1 hour
    )

    from config.email import send_reset_password_email
    base_url = os.getenv("FRONTEND_URL", "http://localhost:8888")
    try:
        await send_reset_password_email(row["email"], token, base_url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send reset email: {exc}")

    accept = request.headers.get("accept", "")
    if "json" in accept:
        return {"message": f"Password reset sent to {row['email']}"}
    return RedirectResponse(f"/admin/user/details/{uid}", status_code=303)
