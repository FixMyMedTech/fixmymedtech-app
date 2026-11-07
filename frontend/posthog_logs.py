"""Dedicated OpenTelemetry log export for PostHog instrumentation."""

import logging
from atexit import register

posthog_log = logging.getLogger("fixmymedtech.posthog")
posthog_log.setLevel(logging.INFO)
posthog_log.propagate = False

_configured = False


def configure_posthog_logs(project_token: str, host: str) -> None:
    """Export only records emitted through ``posthog_log`` to PostHog."""
    global _configured
    if _configured or not project_token or not host:
        return

    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    logger_provider = LoggerProvider()
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{host.rstrip('/')}/i/v1/logs",
                headers={"Authorization": f"Bearer {project_token}"},
            )
        )
    )
    posthog_log.addHandler(LoggingHandler(logger_provider=logger_provider))
    register(logger_provider.shutdown)
    _configured = True
