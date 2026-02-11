"""OpenTelemetry exporter scaffold for Sigma OVERWATCH.

Emits spans/metrics for DecisionEpisodes and DriftEvents.
Requires: pip install opentelemetry-api opentelemetry-sdk

Usage:
    from adapters.otel.otel_exporter import OtelExporter
        exporter = OtelExporter(service_name="sigma-overwatch")
            exporter.export_episode(episode_dict)
                exporter.export_drift(drift_dict)
                """

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
      from opentelemetry import trace, metrics
      from opentelemetry.sdk.trace import TracerProvider
      from opentelemetry.sdk.metrics import MeterProvider
      from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
      from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
      HAS_OTEL = True
except ImportError:
      HAS_OTEL = False


class OtelExporter:
      """Export Sigma OVERWATCH episodes and drift events as OTel spans and metrics."""

    def __init__(self, service_name: str = "sigma-overwatch", endpoint: Optional[str] = None):
              self.service_name = service_name
              self.endpoint = endpoint
              self._tracer = None
              self._meter = None

        if not HAS_OTEL:
                      logger.warning("opentelemetry packages not installed; OtelExporter is a no-op")
                      return

        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service_name)

        reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
        metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
        self._meter = metrics.get_meter(service_name)

        self._episode_counter = self._meter.create_counter(
                      "overwatch.episodes.total", description="Total decision episodes processed"
        )
        self._drift_counter = self._meter.create_counter(
                      "overwatch.drifts.total", description="Total drift events detected"
        )
        self._latency_histogram = self._meter.create_histogram(
                      "overwatch.episode.duration_ms", description="Episode duration in ms"
        )

    def export_episode(self, episode: Dict[str, Any]) -> None:
              if not self._tracer:
                            return
                        with self._tracer.start_as_current_span("decision_episode") as span:
                                      span.set_attribute("episode.id", episode.get("episodeId", ""))
                                      span.set_attribute("episode.decision_type", episode.get("decisionType", ""))
                                      span.set_attribute("episode.outcome", episode.get("outcome", {}).get("status", ""))
                                      degrade_step = episode.get("degrade", {}).get("step", "none")
                                      span.set_attribute("episode.degrade_step", degrade_step)

            duration = episode.get("telemetry", {}).get("endToEndMs", 0)
            self._latency_histogram.record(duration, {"decision_type": episode.get("decisionType", "")})
            self._episode_counter.add(1, {"decision_type": episode.get("decisionType", ""), "outcome": episode.get("outcome", {}).get("status", "")})

    def export_drift(self, drift: Dict[str, Any]) -> None:
              if not self._tracer:
                            return
                        with self._tracer.start_as_current_span("drift_event") as span:
                                      span.set_attribute("drift.id", drift.get("driftId", ""))
                                      span.set_attribute("drift.type", drift.get("driftType", ""))
                                      span.set_attribute("drift.severity", drift.get("severity", ""))
                                      span.set_attribute("drift.episode_id", drift.get("episodeId", ""))
                                      self._drift_counter.add(1, {"drift_type": drift.get("driftType", ""), "severity": drift.get("severity", "")})
