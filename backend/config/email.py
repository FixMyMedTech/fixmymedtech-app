"""FastAPI-Mail configuration.

Reads SMTP settings from environment variables. When MAIL_SERVER is empty or
missing, emails are logged to the console instead of being sent (useful for
local development without an SMTP server).
"""

import os
import logging
from pathlib import Path
from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("email")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

MAIL_SERVER   = os.getenv("MAIL_SERVER", "")
MAIL_PORT     = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM     = os.getenv("MAIL_FROM", "noreply@fixmymedtech.org")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "FixMyMedTech")
LOGO_URL      = os.getenv("LOGO_URL", "https://fndvnrrmzfstflialpag.supabase.co/storage/v1/object/public/assets/fixmymedtech_africa.png")

USE_TLS = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
USE_SSL = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"

_email_enabled = bool(MAIL_SERVER)

_fm: FastMail | None = None

if _email_enabled:
    _conf = ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_FROM=MAIL_FROM,
        MAIL_FROM_NAME=MAIL_FROM_NAME,
        MAIL_STARTTLS=USE_TLS,
        MAIL_SSL_TLS=USE_SSL,
        USE_CREDENTIALS=bool(MAIL_USERNAME),
        VALIDATE_CERTS=True,
    )
    _fm = FastMail(_conf)


async def send_message(
    subject: str,
    to: list[str],
    html: str,
) -> None:
    """Send an HTML email, or log it if SMTP is not configured."""
    msg = MessageSchema(
        subject=subject,
        recipients=to,
        body=html,
        subtype=MessageType.html,
    )
    if _fm is not None:
        await _fm.send_message(msg)
        logger.info("Email sent to %s: %s", to, subject)
    else:
        logger.warning(
            "MAIL_SERVER not configured — email NOT sent.\n"
            "  To: %s\n  Subject: %s\n  (enable by setting MAIL_SERVER in .env)",
            to, subject,
        )


def _render(template_name: str, **context) -> str:
    """Render an HTML email template with the shared logo context."""
    ctx = {"logo_url": LOGO_URL}
    ctx.update(context)
    return _jinja.get_template(template_name).render(**ctx)


async def send_verification_email(email: str, token: str, base_url: str) -> None:
    # base_url must be the BACKEND's public URL, because /api/auth/verify is a
    # backend route (the frontend has no such path and would fall through to login).
    api_base = os.getenv("PUBLIC_API_URL", base_url)
    link = f"{api_base.rstrip('/')}/api/auth/verify?token={token}"
    html = _render(
        "email_verification.html",
        link=link,
        email=email,
    )
    await send_message("Verify your FixMyMedTech account", [email], html)


async def send_reset_password_email(email: str, token: str, base_url: str) -> None:
    link = f"{base_url.rstrip('/')}/reset-password?token={token}"
    html = _render(
        "email_reset_password.html",
        link=link,
        email=email,
    )
    await send_message("FixMyMedTech – password reset", [email], html)


async def send_invitation_email(email: str, token: str, base_url: str) -> None:
    """Invitation for an admin-created user.

    Uses the reset-password token contract (aud ``fastapi-users:reset-password``)
    so the produced link lets the invited user set their own password, after which
    they can log in.
    """
    link = f"{base_url.rstrip('/')}/reset-password?token={token}"
    html = _render(
        "email_invitation.html",
        link=link,
        email=email,
    )
    await send_message("You've been invited to FixMyMedTech", [email], html)


async def send_welcome_email(email: str, full_name: str) -> None:
    html = (
        f"<h2>Welcome to FixMyMedTech!</h2>"
        f"<p>Hi {full_name},</p>"
        f"<p>Your account has been created. You can now log in.</p>"
        f"<p>If you need help, reply to this email.</p>"
    )
    await send_message("Welcome to FixMyMedTech", [email], html)
