"""Discord webhooks: feedback forum threads and the welcome message.

Configuration (environment variables, see docker-compose.yml / .env):

* ``DISCORD_FEEDBACK_WEBHOOK_URL`` — webhook of a Discord *forum* channel
  (Channel settings → Integrations → Webhooks). Unset disables posting; the
  feedback is still stored in the database.
* ``DISCORD_FEEDBACK_TAG_ID`` / ``DISCORD_ISSUE_TAG_ID`` — optional forum tag
  ids applied to the new thread (right-click a tag with Developer Mode on →
  Copy ID).
* ``DISCORD_WELCOME_WEBHOOK_URL`` — webhook of the welcome channel. When set,
  a welcome message mentioning the user is posted the first time an app
  account is linked to a Discord account.

A webhook on a forum channel creates a new thread per message when
``thread_name`` is set, so no bot is needed.
"""

import json
import os
from typing import Optional

import httpx

DISCORD_FEEDBACK_WEBHOOK_URL = os.getenv("DISCORD_FEEDBACK_WEBHOOK_URL", "")
DISCORD_WELCOME_WEBHOOK_URL = os.getenv("DISCORD_WELCOME_WEBHOOK_URL", "")
DISCORD_TAG_IDS = {
    "feedback": os.getenv("DISCORD_FEEDBACK_TAG_ID", ""),
    "issue": os.getenv("DISCORD_ISSUE_TAG_ID", ""),
}

# Discord limits: thread names are capped at 100 characters, message content
# at 2000.
THREAD_NAME_MAX = 100
CONTENT_MAX = 2000


def discord_enabled() -> bool:
    return bool(DISCORD_FEEDBACK_WEBHOOK_URL)


def welcome_enabled() -> bool:
    return bool(DISCORD_WELCOME_WEBHOOK_URL)


async def _execute(url: str, payload: dict,
                   attachment: Optional[tuple[str, bytes, str]] = None) -> dict:
    """Run a webhook and return the created message. Raises on any failure."""
    params = {"wait": "true"}  # return the created message
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        if attachment:
            filename, data, ctype = attachment
            r = await client.post(
                url, params=params,
                data={"payload_json": json.dumps(payload)},
                files={"files[0]": (filename, data, ctype)},
            )
        else:
            r = await client.post(url, params=params, json=payload)
    r.raise_for_status()
    return r.json()


async def create_forum_thread(
    title: str,
    content: str,
    kind: str,
    attachment: Optional[tuple[str, bytes, str]] = None,
) -> str:
    """Create a forum thread and return its id. Raises on any failure.

    ``attachment`` is an optional ``(filename, bytes, content_type)`` posted as
    a file on the thread's first message.
    """
    payload = {
        "thread_name": title[:THREAD_NAME_MAX],
        "content": content[:CONTENT_MAX],
        # Text comes from untrusted users: never let it ping @everyone/@here,
        # roles or members.
        "allowed_mentions": {"parse": []},
    }
    tag_id = DISCORD_TAG_IDS.get(kind)
    if tag_id:
        payload["applied_tags"] = [tag_id]

    message = await _execute(DISCORD_FEEDBACK_WEBHOOK_URL, payload, attachment)
    # For a forum post, the first message's channel is the new thread.
    return str(message["channel_id"])


async def post_welcome(content: str, mention_user_id: str) -> None:
    """Post in the welcome channel. Raises on any failure.

    Only ``mention_user_id`` may be pinged: the text includes names the user
    typed, so @everyone, roles and other users stay disabled.
    """
    await _execute(DISCORD_WELCOME_WEBHOOK_URL, {
        "content": content[:CONTENT_MAX],
        "allowed_mentions": {"parse": [], "users": [mention_user_id]},
    })
