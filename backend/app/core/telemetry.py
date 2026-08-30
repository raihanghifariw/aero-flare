"""
OpenTelemetry tracing + Prometheus metrics setup.
Observability pillar: metrics (Prometheus) + traces (OTel → Grafana Cloud).
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI

logger = structlog.get_logger()


def setup_telemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing and Prometheus metrics for the FastAPI app."""
    from app.core.config import get_settings
    settings = get_settings()

    # --- OpenTelemetry Tracing ---
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": "aero-flare-backend",
            "service.version": "1.0.0",
            "deployment.environment": settings.ENVIRONMENT,
        })
        provider = TracerProvider(resource=resource)

        if settings.GRAFANA_OTLP_ENDPOINT:
            import base64

            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            endpoint = settings.GRAFANA_OTLP_ENDPOINT.strip().rstrip("/")
            if not endpoint.endswith("/v1/traces"):
                endpoint = f"{endpoint}/v1/traces"

            auth_header = ""
            if settings.GRAFANA_INSTANCE_ID and settings.GRAFANA_API_TOKEN:
                creds = f"{settings.GRAFANA_INSTANCE_ID}:{settings.GRAFANA_API_TOKEN}"
                b64_creds = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
                auth_header = f"Basic {b64_creds}"
            elif settings.GRAFANA_API_TOKEN:
                auth_header = f"Bearer {settings.GRAFANA_API_TOKEN}"

            headers = {"Authorization": auth_header} if auth_header else {}

            exporter = OTLPSpanExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=10,
            )
            # Flush every 1 second in dev/prod so traces appear immediately in Grafana
            span_processor = BatchSpanProcessor(
                exporter,
                schedule_delay_millis=1000,
                max_export_batch_size=64,
            )
            provider.add_span_processor(span_processor)
            logger.info(
                "otel_tracing_enabled",
                service_name="aero-flare-backend",
                endpoint=endpoint,
            )
        else:
            logger.info("otel_tracing_disabled", reason="GRAFANA_OTLP_ENDPOINT not set")


        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

    except ImportError as e:
        logger.warning("otel_import_failed", error=str(e))

    # --- Prometheus Metrics ---
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            excluded_handlers=["/api/v1/health", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("prometheus_metrics_enabled", endpoint="/metrics")

    except ImportError as e:
        logger.warning("prometheus_import_failed", error=str(e))
