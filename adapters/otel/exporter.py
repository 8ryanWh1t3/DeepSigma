"""OpenTelemetry exporter for DeepSigma episodes. Closes #6.

Converts sealed episodes to OpenTelemetry spans and metrics.

Exporter selection (in priority order):
1. OTLP gRPC — when OTEL_EXPORTER_OTLP_ENDPOINT is set (e.g. http://localhost:4317)
2. OTLP HTTP — when OTEL_EXPORTER_OTLP_ENDPOINT ends with :4318 or /v1/traces
3. Console   — fallback when no endpoint is configured

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT  gRPC or HTTP OTLP collector endpoint
    OTEL_SERVICE_NAME            Override service name (default: sigma-overwatch)
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import StatusCode

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPGrpcExporter
    HAS_OTLP_GRPC = True
except ImportError:
    HAS_OTLP_GRPC = False

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHttpExporter
    HAS_OTLP_HTTP = True
except ImportError:
    HAS_OTLP_HTTP = False


def _build_exporter(endpoint: str | None):
    """Return the best available span exporter for the given endpoint."""
    if endpoint:
        # HTTP endpoint (port 4318 or /v1/traces path)
        if ":4318" in endpoint or "/v1/traces" in endpoint:
            if HAS_OTLP_HTTP:
                logger.info("OTel: using OTLP HTTP exporter → %s", endpoint)
                return OTLPHttpExporter(endpoint=endpoint)
        # Default to gRPC
        if HAS_OTLP_GRPC:
            logger.info("OTel: using OTLP gRPC exporter → %s", endpoint)
            return OTLPGrpcExporter(endpoint=endpoint)
        if HAS_OTLP_HTTP:
            logger.info("OTel: falling back to OTLP HTTP exporter → %s", endpoint)
            return OTLPHttpExporter(endpoint=endpoint)
        logger.warning("OTel: OTLP endpoint set but no OTLP exporter installed; falling back to console")
    logger.info("OTel: using console exporter")
    return ConsoleSpanExporter()


class OtelExporter:
    """Export episodes and drift events as OTel spans and metrics.

    Reads OTEL_EXPORTER_OTLP_ENDPOINT from the environment if no endpoint
    is passed explicitly. Uses BatchSpanProcessor when an OTLP endpoint is
    configured; SimpleSpanProcessor for the console fallback.
    """

    def __init__(self, service_name: str = "sigma-overwatch", endpoint: str | None = None):
        self.service_name = os.environ.get("OTEL_SERVICE_NAME", service_name)
        self.endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        self._tracer = None
        self._meter = None

        if not HAS_OTEL:
            logger.warning("opentelemetry packages not installed; OtelExporter is a no-op")
            return

        span_exporter = _build_exporter(self.endpoint)
        processor = (
            BatchSpanProcessor(span_exporter) if self.endpoint
            else SimpleSpanProcessor(span_exporter)
        )

        provider = TracerProvider(
            resource=Resource.create({"service.name": self.service_name}),
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        self._tracer = trace.get_tracer(self.service_name)
        self._episode_counter = None
        self._latency_histogram = None
        self._drift_counter = None

    def export_episode(self, episode: Dict[str, Any]) -> None:
        """Export a sealed decision episode as an OTel span tree."""
        if not self._tracer:
            return

        with self._tracer.start_as_current_span("decision_episode") as span:
            span.set_attribute("episode.id", episode.get("episodeId", ""))
            span.set_attribute("episode.decision_type", episode.get("decisionType", ""))

            telemetry = episode.get("telemetry", {})
            stage_ms = telemetry.get("stageMs", {})

            for phase in ("context", "plan", "act", "verify"):
                with self._tracer.start_as_current_span(f"phase.{phase}") as child:
                    child.set_attribute("phase.name", phase)
                    child.set_attribute("phase.duration_ms", stage_ms.get(phase, 0))

            degrade = episode.get("degrade", {})
            degrade_step = degrade.get("step", "none")
            if degrade_step and degrade_step != "none":
                span.add_event(
                    "degrade_triggered",
                    attributes={"degrade.step": degrade_step},
                )

            span.set_attribute("episode.degrade_step", degrade_step)

            outcome = episode.get("outcome", {})
            if outcome.get("code") == "success":
                span.set_status(StatusCode.OK)
            elif outcome.get("code") in ("fail",):
                span.set_status(StatusCode.ERROR, outcome.get("reason", ""))

            return {
                "status": "exported",
                "episodeId": episode.get("episodeId"),
                "spansCreated": 5,
            }

    def export_drift(self, drift: Dict[str, Any]) -> None:
        """Export a drift event as an OTel span."""
        if not self._tracer:
            return

        with self._tracer.start_as_current_span("drift_event") as span:
            span.set_attribute("drift.id", drift.get("driftId", ""))
            span.set_attribute("drift.type", drift.get("driftType", ""))
            span.set_attribute("drift.episode_id", drift.get("episodeId", ""))

