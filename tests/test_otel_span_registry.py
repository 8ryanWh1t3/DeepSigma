"""CI gate: every OTel span name and attribute key must be registered in spans.py.

This test reads the exporter source and verifies that all
start_as_current_span() and set_attribute() calls use constants
from adapters.otel.spans — no unregistered string literals allowed.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.otel.spans import (
    ALL_ATTRIBUTE_KEYS,
    ALL_METRIC_NAMES,
    ALL_SPAN_NAMES,
    ATTR_COHERENCE_DIMENSION_PREFIX,
    SPAN_PHASE_PREFIX,
    SPAN_PHASE_NAMES,
)

EXPORTER_PATH = Path(__file__).resolve().parents[1] / "adapters" / "otel" / "exporter.py"


def _parse_exporter() -> ast.Module:
    return ast.parse(EXPORTER_PATH.read_text(encoding="utf-8"), filename=str(EXPORTER_PATH))


class TestSpanNamesRegistered:
    """All span names in exporter.py must come from the spans.py registry."""

    def test_spans_module_exports_all_names(self):
        """spans.py ALL_SPAN_NAMES covers the three root span types."""
        assert len(ALL_SPAN_NAMES) >= 3
        assert "decision_episode" in ALL_SPAN_NAMES
        assert "drift_event" in ALL_SPAN_NAMES
        assert "coherence_evaluation" in ALL_SPAN_NAMES

    def test_phase_names_registered(self):
        """The four phase names are all registered."""
        assert SPAN_PHASE_NAMES == {"context", "plan", "act", "verify"}

    def test_no_hardcoded_span_names_in_exporter(self):
        """Exporter must not use string literals for span names.

        We look for calls to start_as_current_span(\"...\") and verify
        the argument is either a constant reference or an f-string using
        the registered prefix.
        """
        tree = _parse_exporter()
        violations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # Match: *.start_as_current_span(...)
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "start_as_current_span"):
                continue
            if not node.args:
                continue
            arg = node.args[0]
            # String literal → violation
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                violations.append(f"line {arg.lineno}: hardcoded span name '{arg.value}'")
            # JoinedStr (f-string) is OK if it uses the phase prefix constant

        assert not violations, (
            "Hardcoded span name strings found in exporter.py. "
            "Use constants from adapters.otel.spans instead:\n"
            + "\n".join(violations)
        )


class TestAttributeKeysRegistered:
    """All attribute keys in exporter.py must come from the spans.py registry."""

    def test_attribute_keys_use_namespace(self):
        """All registered attribute keys use deepsigma.* namespace."""
        for key in ALL_ATTRIBUTE_KEYS:
            assert key.startswith("deepsigma."), f"Attribute '{key}' missing deepsigma. prefix"

    def test_no_hardcoded_attribute_keys_in_exporter(self):
        """Exporter must not use string literals for set_attribute keys."""
        tree = _parse_exporter()
        violations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "set_attribute"):
                continue
            if not node.args:
                continue
            key_arg = node.args[0]
            # String literal → violation
            if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str):
                violations.append(f"line {key_arg.lineno}: hardcoded attribute key '{key_arg.value}'")
            # JoinedStr (f-string) is OK if it uses a registered prefix

        assert not violations, (
            "Hardcoded attribute key strings found in exporter.py. "
            "Use constants from adapters.otel.spans instead:\n"
            + "\n".join(violations)
        )


class TestMetricNamesRegistered:
    """All metric names must be registered in spans.py."""

    def test_metric_names_complete(self):
        assert len(ALL_METRIC_NAMES) == 4
        assert "sigma.episodes.total" in ALL_METRIC_NAMES
        assert "sigma.episode.latency_ms" in ALL_METRIC_NAMES
        assert "sigma.drift.total" in ALL_METRIC_NAMES
        assert "sigma.coherence.score" in ALL_METRIC_NAMES

    def test_no_hardcoded_metric_names_in_exporter(self):
        """Exporter must not use string literals for metric name= args."""
        tree = _parse_exporter()
        violations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in ("create_counter", "create_histogram", "create_observable_gauge"):
                continue
            for kw in node.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    violations.append(f"line {kw.value.lineno}: hardcoded metric name '{kw.value.value}'")

        assert not violations, (
            "Hardcoded metric name strings found in exporter.py. "
            "Use constants from adapters.otel.spans instead:\n"
            + "\n".join(violations)
        )


class TestSpansModuleIntegrity:
    """Structural checks on the spans.py registry itself."""

    def test_all_span_names_is_frozenset(self):
        assert isinstance(ALL_SPAN_NAMES, frozenset)

    def test_all_attribute_keys_is_frozenset(self):
        assert isinstance(ALL_ATTRIBUTE_KEYS, frozenset)

    def test_all_metric_names_is_frozenset(self):
        assert isinstance(ALL_METRIC_NAMES, frozenset)

    def test_coherence_dimension_prefix_matches(self):
        """Dynamic coherence dimension attributes use the registered prefix."""
        assert ATTR_COHERENCE_DIMENSION_PREFIX == "deepsigma.coherence"

    def test_phase_prefix_matches(self):
        """Dynamic phase span names use the registered prefix."""
        assert SPAN_PHASE_PREFIX == "phase"
