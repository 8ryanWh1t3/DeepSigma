"""Lightweight Prometheus exposition metrics for DeepSigma.

This module avoids hard runtime dependency on prometheus_client while still
exposing Prometheus-compatible text format from /metrics.
"""

from __future__ import annotations

import math
import threading
from collections import defaultdict
from dataclasses import dataclass


def _fmt_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    parts = []
    for k in sorted(labels):
        v = labels[k].replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        parts.append(f'{k}="{v}"')
    return "{" + ",".join(parts) + "}"


@dataclass
class _HistogramState:
    buckets: list[float]
    counts: list[int]
    sum_value: float = 0.0
    total_count: int = 0


class PromMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._gauges: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(dict)
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(dict)
        self._histograms: dict[str, _HistogramState] = {}

    @staticmethod
    def _key(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((str(k), str(v)) for k, v in labels.items()))

    @staticmethod
    def _labels_from_key(key: tuple[tuple[str, str], ...]) -> dict[str, str]:
        return dict(key)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._gauges[name][self._key(labels)] = float(value)

    def inc_counter(self, name: str, inc: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            k = self._key(labels)
            self._counters[name][k] = self._counters[name].get(k, 0.0) + float(inc)

    def set_counter_floor(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            k = self._key(labels)
            cur = self._counters[name].get(k, 0.0)
            self._counters[name][k] = max(cur, float(value))

    def define_histogram(self, name: str, buckets: list[float]) -> None:
        with self._lock:
            clean = sorted(b for b in buckets if b > 0)
            if not clean:
                clean = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
            self._histograms[name] = _HistogramState(
                buckets=clean,
                counts=[0 for _ in clean],
            )

    def observe_histogram(self, name: str, value: float) -> None:
        with self._lock:
            if name not in self._histograms:
                self.define_histogram(name, [])
            h = self._histograms[name]
            v = 0.0 if math.isnan(value) or value < 0 else float(value)
            h.sum_value += v
            h.total_count += 1
            for i, bound in enumerate(h.buckets):
                if v <= bound:
                    h.counts[i] += 1

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, series in sorted(self._gauges.items()):
                lines.append(f"# TYPE {name} gauge")
                for k, v in sorted(series.items()):
                    lines.append(f"{name}{_fmt_labels(self._labels_from_key(k))} {v}")

            for name, series in sorted(self._counters.items()):
                lines.append(f"# TYPE {name} counter")
                for k, v in sorted(series.items()):
                    lines.append(f"{name}{_fmt_labels(self._labels_from_key(k))} {v}")

            for name, h in sorted(self._histograms.items()):
                lines.append(f"# TYPE {name} histogram")
                cumulative = 0
                for i, bound in enumerate(h.buckets):
                    cumulative += h.counts[i]
                    lines.append(f'{name}_bucket{{le="{bound:g}"}} {cumulative}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {h.total_count}')
                lines.append(f"{name}_sum {h.sum_value}")
                lines.append(f"{name}_count {h.total_count}")

        lines.append("")
        return "\n".join(lines)


PROM_METRICS = PromMetrics()

# Required histograms
PROM_METRICS.define_histogram(
    "deepsigma_packet_seal_duration_seconds",
    [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)
PROM_METRICS.define_histogram(
    "deepsigma_iris_query_duration_seconds",
    [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2],
)
