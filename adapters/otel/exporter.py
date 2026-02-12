"""OpenTelemetry exporter for DeepSigma episodes.

Closes #6.

Converts sealed episodes to OpenTelemetry spans and metrics.

Usage:
    from adapters.otel.exporter import export_episode
        export_episode(episode_dict, endpoint="http://localhost:4317")
        """
from __future__ import annotations

from typing import Any, Dict, Optional

try:
      from opentelemetry import trace
      from opentelemetry.sdk.trace import TracerProvider
      from opentelemetry.sdk.trace.export import SimpleSpanProcessor
      from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
      from opentelemetry.sdk.resources import Resource
      from opentelemetry.trace import StatusCode
      HAS_OTEL = True
except ImportError:
      HAS_OTEL = False


def _setup_tracer(endpoint: str) -> Any:
      """Configure OTel tracer with OTLP exporter."""
      if not HAS_OTEL:
                raise ImportError(
                              "opentelemetry packages not installed. "
                              "pip install opentelemetry-sdk opentelemetry-exporter-otlp"
                )

      resource = Resource.create({"service.name": "deepsigma"})
      provider = TracerProvider(resource=resource)
      exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
      provider.add_span_processor(SimpleSpanProcessor(exporter))
      trace.set_tracer_provider(provider)
      return trace.get_tracer("deepsigma.exporter")


def export_episode(episode: Dict[str, Any], endpoint: str = "http://localhost:4317") -> Dict[str, Any]:
      """Export a sealed episode as OTel spans.

          Creates a parent span for the episode and child spans for key phases.
              Drift events are added as span events.

                  Args:
                          episode: Sealed episode dict conforming to episode.schema.json.
                                  endpoint: OTLP gRPC endpoint (default: localhost:4317).

                                      Returns:
                                              Summary dict with span IDs and export status.
                                                  """
      tracer = _setup_tracer(endpoint)
      telemetry = episode.get("telemetry", {})
      stage_ms = telemetry.get("stageMs", {})
      outcome = episode.get("outcome", {})

    # Parent span: the episode
      with tracer.start_as_current_span(
                name=f"episode.{episode.get('decisionType', 'unknown')}",
                attributes={
                              "deepsigma.episode_id": episode.get("episodeId", ""),
                              "deepsigma.decision_type": episode.get("decisionType", ""),
                              "deepsigma.decision_window_ms": episode.get("decisionWindowMs", 0),
                              "deepsigma.outcome_code": outcome.get("code", ""),
                              "deepsigma.end_to_end_ms": telemetry.get("endToEndMs", 0),
                              "deepsigma.fallback_used": telemetry.get("fallbackUsed", False),
                },
      ) as parent_span:

                # Child span: context phase
                with tracer.start_as_current_span(
                              name="phase.context",
                              attributes={"deepsigma.phase": "context", "deepsigma.duration_ms": stage_ms.get("context", 0)},
                ):
                              pass

                # Child span: plan phase
                with tracer.start_as_current_span(
                              name="phase.plan",
                              attributes={"deepsigma.phase": "plan", "deepsigma.duration_ms": stage_ms.get("plan", 0)},
                ):
                              pass

                # Child span: act phase
                with tracer.start_as_current_span(
                              name="phase.act",
                              attributes={"deepsigma.phase": "act", "deepsigma.duration_ms": stage_ms.get("act", 0)},
                ):
                              pass

                # Child span: verify phase
                verification = episode.get("verification", {})
                with tracer.start_as_current_span(
                              name="phase.verify",
                              attributes={
                                                "deepsigma.phase": "verify",
                                                "deepsigma.duration_ms": stage_ms.get("verify", 0),
                                                "deepsigma.verification_result": verification.get("result", "na"),
                              },
                ):
                              pass

                # Degrade info as span event
                degrade = episode.get("degrade", {})
        if degrade.get("step") and degrade["step"] != "none":
                      parent_span.add_event(
                                        "degrade_triggered",
                                        attributes={
                                                              "deepsigma.degrade_step": degrade["step"],
                                        },
                      )

        # Set span status based on outcome
        if outcome.get("code") == "success":
                      parent_span.set_status(StatusCode.OK)
elif outcome.get("code") in ("fail",):
            parent_span.set_status(StatusCode.ERROR, outcome.get("reason", ""))

    return {
              "status": "exported",
              "episodeId": episode.get("episodeId"),
              "endpoint": endpoint,
              "spansCreated": 5,
    }
