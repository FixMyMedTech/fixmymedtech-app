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
# `or` rather than a getenv default: compose passes unset variables through
# as empty strings, and int("") would crash the whole email module.
MAIL_PORT     = int(os.getenv("MAIL_PORT") or 587)
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM     = os.getenv("MAIL_FROM") or "noreply@fixmymedtech.org"
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME") or "FixMyMedTech"
LOGO_URL      = os.getenv("LOGO_URL") or "https://fndvnrrmzfstflialpag.supabase.co/storage/v1/object/public/assets/fixmymedtech_africa.png"

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


# ── Onboarding (migration 029) ──────────────────────────────────────────────
# One template, email_onboarding.html; Jinja autoescape is off for these
# templates, so every user-written value is escaped here.

def _esc(value) -> str:
    from html import escape
    return escape(str(value or ""))


async def _send_onboarding(email: str, subject: str, heading: str, paragraphs: list,
                           link: str = "", button: str = "", message: str = "",
                           benefits: list | None = None, footer: str = "") -> None:
    html = _render(
        "email_onboarding.html",
        subject=_esc(subject),
        heading=_esc(heading),
        paragraphs=[_esc(p) for p in paragraphs],
        message=_esc(message),
        benefits=[_esc(b) for b in (benefits or [])],
        link=link,
        button=_esc(button),
        footer=_esc(footer),
    )
    await send_message(subject, [email], html)


async def send_clinic_invitation_email(email: str, inviter: str, message: str, link: str) -> None:
    """An engineer invites a clinic. Explains the vision and what the clinic gets."""
    await _send_onboarding(
        email,
        subject=f"{inviter} invites your clinic to FixMyMedTech",
        heading="Keep your medical equipment working",
        paragraphs=[
            f"{inviter}, a biomedical engineer in the FixMyMedTech community, invites your clinic to join.",
            "FixMyMedTech is a free platform where clinics and biomedical engineers keep medical devices "
            "working: every device gets a QR tag, staff report a fault in seconds, and your engineers "
            "track repairs and maintenance in one place.",
        ],
        message=message,
        benefits=[
            "A QR tag on each device: anyone can report a fault from a phone.",
            "A clear list of your equipment, its status and its maintenance history.",
            "Engineers you trust, named by you, register and look after your devices.",
        ],
        link=link,
        button="Set up your clinic",
        footer="If you didn't expect this email, you can safely ignore it.",
    )


async def send_engineer_invitation_email(email: str, clinic: str, inviter: str, link: str) -> None:
    """A clinic invites an engineer to become one of its responsible engineers."""
    await _send_onboarding(
        email,
        subject=f"{clinic} invites you to look after its devices on FixMyMedTech",
        heading=f"{clinic} invites you",
        paragraphs=[
            f"{inviter} named you a responsible engineer for {clinic} on FixMyMedTech.",
            "Create your account and finish three short welcome steps (your profile, a picture and a "
            "community talk). You can then register devices for the clinic.",
        ],
        link=link,
        button="Create your account",
        footer="If you didn't expect this email, you can safely ignore it.",
    )


async def send_engineer_confirmed_email(email: str, name: str, clinic: str,
                                        ready: bool, link: str) -> None:
    """A clinic confirmed an engineer as one of its responsible engineers."""
    if ready:
        paragraphs = [f"Hi {name},", f"{clinic} confirmed that you can register devices in its name."]
    else:
        paragraphs = [
            f"Hi {name},",
            f"{clinic} confirmed you as one of its responsible engineers.",
            "You can register devices for it as soon as your welcome steps are done"
            " (and, for a new clinic, once its clinic talk has taken place).",
        ]
    await _send_onboarding(
        email,
        subject=f"{clinic} confirmed you on FixMyMedTech",
        heading="You're confirmed",
        paragraphs=paragraphs,
        link=link,
        button="Open FixMyMedTech",
    )
