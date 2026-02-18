"""Tests for OTel exporter — metrics, spans, and no-op fallback."""
import pytest


SAMPLE_EPISODE = {
    "episodeId": "ep-otel-001",
    "decisionType": "deploy",
    "outcome": {"code": "success"},
    "degrade": {"step": "none"},
    "telemetry": {
        "endToEndMs": 1200,
        "stageMs": {"context": 40, "plan": 30, "act": 20, "verify": 10},
    },
}

SAMPLE_DRIFT = {
    "driftId": "drift-otel-001",
    "driftType": "freshness",
    "severity": "yellow",
    "episodeId": "ep-otel-001",
}

SAMPLE_COHERENCE = {
    "overall_score": 78.5,
    "grade": "B",
    "dimensions": [
        {"name": "policy_adherence", "score": 80.0},
        {"name": "outcome_health", "score": 70.0},
        {"name": "drift_control", "score": 90.0},
        {"name": "memory_completeness", "score": 65.0},
    ],
}


class TestNoOpFallback:
    """When opentelemetry is not installed, exporter is a no-op."""

    def test_export_episode_noop(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            assert exporter._tracer is None
            assert exporter._meter is None
            result = exporter.export_episode(SAMPLE_EPISODE)
            assert result is None
        finally:
            mod.HAS_OTEL = original

    def test_export_drift_noop(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            exporter.export_drift(SAMPLE_DRIFT)  # should not raise
        finally:
            mod.HAS_OTEL = original

    def test_export_coherence_noop(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            exporter.export_coherence(SAMPLE_COHERENCE)  # should not raise
            # Score is still recorded for the gauge callback
            assert exporter._coherence_score == 78.5
        finally:
            mod.HAS_OTEL = original


class TestExporterAttributes:
    """Test attribute handling without requiring OTel runtime."""

    def test_service_name_default(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            assert exporter.service_name == "sigma-overwatch"
        finally:
            mod.HAS_OTEL = original

    def test_service_name_custom(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter(service_name="custom-svc")
            assert exporter.service_name == "custom-svc"
        finally:
            mod.HAS_OTEL = original

    def test_endpoint_from_env(self, monkeypatch):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")
            exporter = mod.OtelExporter()
            assert exporter.endpoint == "http://collector:4317"
        finally:
            mod.HAS_OTEL = original


class TestCoherenceRecording:
    """Test coherence score recording logic."""

    def test_coherence_score_stored(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            exporter.export_coherence(SAMPLE_COHERENCE)
            assert exporter._coherence_score == 78.5
            assert exporter._coherence_attrs == {"grade": "B"}
        finally:
            mod.HAS_OTEL = original

    def test_coherence_score_updates(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            exporter.export_coherence({"overall_score": 50.0, "grade": "D"})
            assert exporter._coherence_score == 50.0
            exporter.export_coherence({"overall_score": 92.0, "grade": "A"})
            assert exporter._coherence_score == 92.0
            assert exporter._coherence_attrs == {"grade": "A"}
        finally:
            mod.HAS_OTEL = original

    def test_coherence_initial_none(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            assert exporter._coherence_score is None
        finally:
            mod.HAS_OTEL = original


class TestExportMethods:
    """Verify export methods handle edge cases."""

    def test_episode_missing_telemetry(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            result = exporter.export_episode({"episodeId": "ep-bare"})
            assert result is None  # no-op

        finally:
            mod.HAS_OTEL = original

    def test_drift_missing_fields(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            exporter.export_drift({})  # should not raise
        finally:
            mod.HAS_OTEL = original

    def test_episode_with_degrade(self):
        import adapters.otel.exporter as mod
        original = mod.HAS_OTEL
        try:
            mod.HAS_OTEL = False
            exporter = mod.OtelExporter()
            ep = {**SAMPLE_EPISODE, "degrade": {"step": "cache_bundle"}}
            result = exporter.export_episode(ep)
            assert result is None  # no-op without tracer
        finally:
            mod.HAS_OTEL = original


class TestBuildExporter:
    """Test exporter selection logic (requires OTel SDK)."""

    def test_console_fallback_no_endpoint(self):
        """_build_exporter returns ConsoleSpanExporter when no endpoint."""
        try:
            from adapters.otel.exporter import _build_exporter
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            result = _build_exporter(None)
            assert isinstance(result, ConsoleSpanExporter)
        except ImportError:
            pytest.skip("opentelemetry not installed")
