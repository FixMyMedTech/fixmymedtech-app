# config/oauth.py — Authlib OAuth2 client for social login (Google / GitHub / Discord)

import os
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

def register_oauth(app):
    """Register OAuth providers from environment config. Safe to call even if
    providers are not configured (they're simply skipped)."""

    # ── Google ────────────────────────────────────────────────────────────
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if google_client_id and google_client_secret:
        oauth.register(
            name="google",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    # ── GitHub ────────────────────────────────────────────────────────────
    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if github_client_id and github_client_secret:
        oauth.register(
            name="github",
            client_id=github_client_id,
            client_secret=github_client_secret,
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            userinfo_url="https://api.github.com/user",
            client_kwargs={"scope": "user:email"},
        )

    # ── Discord ───────────────────────────────────────────────────────────
    discord_client_id = os.getenv("DISCORD_CLIENT_ID")
    discord_client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    if discord_client_id and discord_client_secret:
        oauth.register(
            name="discord",
            client_id=discord_client_id,
            client_secret=discord_client_secret,
            access_token_url="https://discord.com/api/oauth2/token",
            authorize_url="https://discord.com/api/oauth2/authorize",
            userinfo_endpoint="https://discord.com/api/users/@me",
            client_kwargs={"scope": "identify email"},
        )

    return oauth
