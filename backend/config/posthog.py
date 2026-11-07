"""PostHog error tracking for the API. Disabled when the env vars are empty."""

import os
from atexit import register

from posthog import Posthog


def _init() -> Posthog | None:
    token = os.getenv("POSTHOG_PROJECT_TOKEN")
    host = os.getenv("POSTHOG_HOST")
    if not token or not host:
        return None
    client = Posthog(
        token,
        host=host,
        enable_exception_autocapture=True,
        super_properties={"service": "backend"},
    )
    register(client.shutdown)
    return client


posthog_client = _init()
