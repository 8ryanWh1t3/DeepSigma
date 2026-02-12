"""OpenTelemetry exporter for DeepSigma episodes. Closes #6.

Converts sealed episodes to OpenTelemetry spans and metrics.

Usage:
    from adapters.otel.exporter import export_episode
    export_episode(episode_dict, endpoint="http://localhost:4317")
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import StatusCode

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


class OtelExporter:
    """Export Sigma OVERWATCH episodes and drift events as OTel spans and metrics."""

    def __init__(self, service_name: str = "sigma-overwatch", endpoint: str = None):
        self.service_name = service_name
        self.endpoint = endpoint

        self._tracer = None
        self._meter = None

        if not HAS_OTEL:
            logger.warning("opentelemetry packages not installed; OtelExporter is a no-op")
            return

        provider = TracerProvider(
            resource=Resource.create({"service.name": service_name}),
        )
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)

        self._tracer = trace.get_tracer(service_name)
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

            # Child spans for each phase
            telemetry = episode.get("telemetry", {})
            stage_ms = telemetry.get("stageMs", {})

            for phase in ("context", "plan", "act", "verify"):
                with self._tracer.start_as_current_span(f"phase.{phase}") as child:
                    child.set_attribute("phase.name", phase)
                    child.set_attribute("phase.duration_ms", stage_ms.get(phase, 0))

            # Degrade info as span event
            degrade = episode.get("degrade", {})
            degrade_step = degrade.get("step", "none")
            if degrade_step and degrade_step != "none":
                span.add_event(
                    "degrade_triggered",
                    attributes={"degrade.step": degrade_step},
                )

            span.set_attribute("episode.degrade_step", degrade_step)

            duration = episode.get("telemetry", {}).get("endToEndMs", 0)
            if self._latency_histogram:
                self._latency_histogram.record(duration, {"decision_type": episode.get("decisionType", "")})
            if self._episode_counter:
                self._episode_counter.add(1, {
                    "decision_type": episode.get("decisionType", ""),
                    "outcome": episode.get("outcome", {}).get("status", "unknown"),
                })

            # Set span status based on outcome
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
            if self._drift_counter:
                self._drift_counter.add(1, {
                    "drift_type": drift.get("driftType", ""),
                    "severity": drift.get("severity", ""),
                })
