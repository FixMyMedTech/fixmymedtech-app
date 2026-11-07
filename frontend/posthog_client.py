"""Process-wide PostHog client configuration."""

import os
from atexit import register

from posthog import Posthog
from posthog_logs import configure_posthog_logs


def _is_development() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").lower() in {"development", "dev"}
        or os.getenv("DEBUG", "").lower() in {"1", "true", "yes"}
    )


def _missing_configuration(variable_name: str) -> None:
    if _is_development():
        raise RuntimeError(
            f"{variable_name} variable required by PostHog is missing or un-configured, "
            f"this causes events to be silently missed. This error stops appearing once "
            f"{variable_name} is configured"
        )


def _initialize_posthog() -> Posthog | None:
    project_token = os.getenv("POSTHOG_PROJECT_TOKEN")
    if not project_token:
        _missing_configuration("POSTHOG_PROJECT_TOKEN")
        return None

    host = os.getenv("POSTHOG_HOST")
    if not host:
        _missing_configuration("POSTHOG_HOST")
        return None

    return Posthog(
        project_token,
        host=host,
        enable_exception_autocapture=True,
    )


posthog_client = _initialize_posthog()

if posthog_client is not None:
    register(posthog_client.shutdown)
    configure_posthog_logs(
        project_token=os.environ["POSTHOG_PROJECT_TOKEN"],
        host=os.environ["POSTHOG_HOST"],
    )
