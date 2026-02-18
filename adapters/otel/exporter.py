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
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from opentelemetry import metrics, trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
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
        self._episode_counter = None
        self._latency_histogram = None
        self._drift_counter = None
        self._coherence_score: Optional[float] = None
        self._coherence_attrs: Dict[str, str] = {}

        if not HAS_OTEL:
            logger.warning("opentelemetry packages not installed; OtelExporter is a no-op")
            return

        resource = Resource.create({"service.name": self.service_name})

        # Traces
        span_exporter = _build_exporter(self.endpoint)
        processor = (
            BatchSpanProcessor(span_exporter) if self.endpoint
            else SimpleSpanProcessor(span_exporter)
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(self.service_name)

        # Metrics
        metric_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=60_000,
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        self._meter = metrics.get_meter(self.service_name)

        self._episode_counter = self._meter.create_counter(
            name="sigma.episodes.total",
            description="Total number of exported decision episodes",
            unit="1",
        )
        self._latency_histogram = self._meter.create_histogram(
            name="sigma.episode.latency_ms",
            description="End-to-end episode latency in milliseconds",
            unit="ms",
        )
        self._drift_counter = self._meter.create_counter(
            name="sigma.drift.total",
            description="Total number of drift events",
            unit="1",
        )
        self._meter.create_observable_gauge(
            name="sigma.coherence.score",
            description="Latest coherence score (0-100)",
            unit="1",
            callbacks=[self._observe_coherence],
        )

    def _observe_coherence(self, options):
        """Callback for ObservableGauge — returns last recorded coherence score."""
        if self._coherence_score is not None:
            from opentelemetry.metrics import Observation
            yield Observation(value=self._coherence_score, attributes=self._coherence_attrs)

    def export_episode(self, episode: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Export a sealed decision episode as an OTel span tree + metrics."""
        if not self._tracer:
            return None

        with self._tracer.start_as_current_span("decision_episode") as span:
            episode_id = episode.get("episodeId", "")
            decision_type = episode.get("decisionType", "")
            span.set_attribute("episode.id", episode_id)
            span.set_attribute("episode.decision_type", decision_type)

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
            outcome_code = outcome.get("code", "unknown")
            if outcome_code == "success":
                span.set_status(StatusCode.OK)
            elif outcome_code in ("fail",):
                span.set_status(StatusCode.ERROR, outcome.get("reason", ""))

            # Metrics
            if self._episode_counter:
                self._episode_counter.add(1, {
                    "decision_type": decision_type,
                    "outcome": outcome_code,
                    "degrade_step": degrade_step,
                })
            if self._latency_histogram:
                latency = telemetry.get("endToEndMs", 0)
                if latency > 0:
                    self._latency_histogram.record(latency, {
                        "decision_type": decision_type,
                    })

            return {
                "status": "exported",
                "episodeId": episode_id,
                "spansCreated": 5,
            }

    def export_drift(self, drift: Dict[str, Any]) -> None:
        """Export a drift event as an OTel span + metric."""
        if not self._tracer:
            return

        with self._tracer.start_as_current_span("drift_event") as span:
            drift_type = drift.get("driftType", "")
            severity = drift.get("severity", "")
            span.set_attribute("drift.id", drift.get("driftId", ""))
            span.set_attribute("drift.type", drift_type)
            span.set_attribute("drift.severity", severity)
            span.set_attribute("drift.episode_id", drift.get("episodeId", ""))

        if self._drift_counter:
            self._drift_counter.add(1, {
                "drift_type": drift_type,
                "severity": severity,
            })

    def export_coherence(self, report: Dict[str, Any]) -> None:
        """Record coherence score for the ObservableGauge callback.

        Args:
            report: Dict with keys: overall_score, grade, dimensions (list of
                    dicts with name + score).
        """
        self._coherence_score = report.get("overall_score", 0.0)
        self._coherence_attrs = {"grade": report.get("grade", "?")}

        if not self._tracer:
            return

        # Also emit a span for the coherence evaluation event
        with self._tracer.start_as_current_span("coherence_evaluation") as span:
            span.set_attribute("coherence.score", self._coherence_score)
            span.set_attribute("coherence.grade", report.get("grade", ""))
            for dim in report.get("dimensions", []):
                span.set_attribute(
                    f"coherence.{dim.get('name', 'unknown')}",
                    dim.get("score", 0.0),
                )
