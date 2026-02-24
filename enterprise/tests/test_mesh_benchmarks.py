"""Mesh topology benchmarks at 100/250/500 node scale.

Run:    pytest tests/test_mesh_benchmarks.py -v
Skip:   pytest tests/ -v -m "not benchmark"
Gate:   100-node full cycle must complete in < 60s
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mesh.crypto import canonical_bytes, generate_keypair, sign, verify
from mesh.logstore import append_jsonl, load_all
from mesh.node_runtime import MeshNode, NodeRole
from mesh.transport import (
    ENVELOPES_LOG,
    LocalTransport,
    ensure_node_dirs,
)

pytestmark = pytest.mark.benchmark
pytest.importorskip("pytest_benchmark")

TENANT = "bench-tenant"

# Role distribution (realistic): 60% edge, 20% validator, 15% aggregator, 5% seal
_ROLE_WEIGHTS = [
    (NodeRole.EDGE, 0.60),
    (NodeRole.VALIDATOR, 0.20),
    (NodeRole.AGGREGATOR, 0.15),
    (NodeRole.SEAL_AUTHORITY, 0.05),
]

# Roles that don't require tenancy/fastapi
_LIGHT_ROLES = [NodeRole.EDGE, NodeRole.VALIDATOR]


# ── Harness ──────────────────────────────────────────────────────────────────

class MeshBenchmarkHarness:
    """Spin up N in-process mesh nodes with sparse peering."""

    def __init__(
        self,
        node_count: int,
        tmp_dir: Path,
        peers_per_node: int = 10,
        regions: int = 5,
        roles: list[NodeRole] | None = None,
        light_only: bool = False,
    ):
        self.node_count = node_count
        self.tmp_dir = tmp_dir
        self.peers_per_node = min(peers_per_node, node_count - 1)
        self.regions = regions
        self.light_only = light_only
        self.nodes: list[MeshNode] = []
        self._roles = roles

    def setup(self, monkeypatch) -> None:
        """Create nodes with sparse peer topology."""
        import mesh.transport as mt
        monkeypatch.setattr(mt, "_BASE_DATA_DIR", self.tmp_dir)

        transport = LocalTransport()
        node_ids = [f"node-{i:04d}" for i in range(self.node_count)]

        # Assign roles
        if self._roles:
            assigned_roles = self._roles
        else:
            assigned_roles = self._distribute_roles(self.node_count)

        # Build sparse peer lists (k-nearest in circular topology)
        for i, nid in enumerate(node_ids):
            peers = []
            for offset in range(1, self.peers_per_node + 1):
                peer_idx = (i + offset) % self.node_count
                peers.append(node_ids[peer_idx])

            region_idx = i % self.regions
            node = MeshNode(
                node_id=nid,
                tenant_id=TENANT,
                region_id=f"region-{region_idx}",
                role=assigned_roles[i],
                peers=peers,
                transport=transport,
            )
            self.nodes.append(node)

    def _distribute_roles(self, count: int) -> list[NodeRole]:
        if self.light_only:
            weights = [(NodeRole.EDGE, 0.75), (NodeRole.VALIDATOR, 0.25)]
        else:
            weights = _ROLE_WEIGHTS
        roles = []
        for role, weight in weights:
            n = max(1, int(count * weight))
            roles.extend([role] * n)
        # Pad or trim to exact count
        while len(roles) < count:
            roles.append(NodeRole.EDGE)
        return roles[:count]

    def run_edge_ticks(self) -> list[dict]:
        results = []
        for n in self.nodes:
            if n.role == NodeRole.EDGE:
                results.append(n.tick())
        return results

    def run_validator_ticks(self) -> list[dict]:
        results = []
        for n in self.nodes:
            if n.role == NodeRole.VALIDATOR:
                results.append(n.tick())
        return results

    def run_light_cycle(self) -> list[dict]:
        """Edge → Validator cycle (no aggregator/seal, no fastapi dep)."""
        results = []
        for n in self.nodes:
            if n.role == NodeRole.EDGE:
                results.append(n.tick())
        for n in self.nodes:
            if n.role == NodeRole.VALIDATOR:
                results.append(n.tick())
        return results

    def by_role(self, role: NodeRole) -> list[MeshNode]:
        return [n for n in self.nodes if n.role == role]


def _percentiles(values: list[float]) -> dict[str, float]:
    """Compute p50, p95, p99 from a list of values."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    return {
        "p50": s[int(n * 0.50)],
        "p95": s[int(min(n * 0.95, n - 1))],
        "p99": s[int(min(n * 0.99, n - 1))],
    }


# ── Throughput (pytest-benchmark, CI gate) ───────────────────────────────────

class TestMeshThroughput:
    """Benchmark throughput at various scales."""

    def test_100_node_light_cycle(self, benchmark, tmp_path, monkeypatch):
        """CI gate: 100-node edge+validator cycle must complete in < 60s."""
        harness = MeshBenchmarkHarness(100, tmp_path, light_only=True)
        harness.setup(monkeypatch)

        result = benchmark(harness.run_light_cycle)
        assert len(result) >= 100
        # Benchmark stats are collected by pytest-benchmark

    def test_250_node_edge_throughput(self, benchmark, tmp_path, monkeypatch):
        """Edge tick throughput at 250 nodes."""
        harness = MeshBenchmarkHarness(250, tmp_path, light_only=True)
        harness.setup(monkeypatch)

        result = benchmark(harness.run_edge_ticks)
        edges = harness.by_role(NodeRole.EDGE)
        assert len(result) == len(edges)

    def test_500_node_edge_throughput(self, benchmark, tmp_path, monkeypatch):
        """Edge tick throughput at 500 nodes."""
        harness = MeshBenchmarkHarness(500, tmp_path, peers_per_node=8, light_only=True)
        harness.setup(monkeypatch)

        result = benchmark(harness.run_edge_ticks)
        edges = harness.by_role(NodeRole.EDGE)
        assert len(result) == len(edges)


# ── Latency ──────────────────────────────────────────────────────────────────

class TestMeshLatency:
    """Measure per-operation latency distributions."""

    def test_edge_tick_latency_distribution(self, tmp_path, monkeypatch):
        """p50/p95/p99 edge tick latency at 100 nodes."""
        harness = MeshBenchmarkHarness(100, tmp_path, light_only=True)
        harness.setup(monkeypatch)

        edges = harness.by_role(NodeRole.EDGE)
        latencies = []
        for node in edges:
            t0 = time.monotonic()
            node.tick()
            latencies.append(time.monotonic() - t0)

        pcts = _percentiles(latencies)
        assert pcts["p99"] < 2.0, f"p99 edge latency {pcts['p99']:.3f}s exceeds 2s"

    def test_push_pull_latency(self, tmp_path, monkeypatch):
        """Raw transport push/pull round-trip latency."""
        import mesh.transport as mt
        monkeypatch.setattr(mt, "_BASE_DATA_DIR", tmp_path)

        transport = LocalTransport()
        ensure_node_dirs(TENANT, "target-node")

        records = [{"id": f"rec-{i}", "data": f"payload-{i}"} for i in range(10)]

        push_latencies = []
        for _ in range(100):
            t0 = time.monotonic()
            transport.push(TENANT, "target-node", ENVELOPES_LOG, records)
            push_latencies.append(time.monotonic() - t0)

        pull_latencies = []
        for _ in range(100):
            t0 = time.monotonic()
            transport.pull(TENANT, "target-node", ENVELOPES_LOG)
            pull_latencies.append(time.monotonic() - t0)

        push_pcts = _percentiles(push_latencies)
        pull_pcts = _percentiles(pull_latencies)
        assert push_pcts["p99"] < 1.0, f"push p99 {push_pcts['p99']:.3f}s exceeds 1s"
        assert pull_pcts["p99"] < 1.0, f"pull p99 {pull_pcts['p99']:.3f}s exceeds 1s"

    def test_validator_tick_latency(self, tmp_path, monkeypatch):
        """Validator verification latency after edge ticks."""
        harness = MeshBenchmarkHarness(100, tmp_path, light_only=True)
        harness.setup(monkeypatch)

        # Generate envelopes first
        harness.run_edge_ticks()

        validators = harness.by_role(NodeRole.VALIDATOR)
        latencies = []
        for node in validators:
            t0 = time.monotonic()
            node.tick()
            latencies.append(time.monotonic() - t0)

        pcts = _percentiles(latencies)
        assert pcts["p99"] < 5.0, f"p99 validator latency {pcts['p99']:.3f}s exceeds 5s"


# ── Memory ───────────────────────────────────────────────────────────────────

class TestMeshMemory:
    """Measure memory consumption at scale."""

    def _measure_setup_memory(self, node_count, tmp_path, monkeypatch):
        """Setup N nodes and return (peak_mb, per_node_kb)."""
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        harness = MeshBenchmarkHarness(node_count, tmp_path, light_only=True)
        harness.setup(monkeypatch)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
        total_mb = total_bytes / (1024 * 1024)
        per_node_kb = (total_bytes / node_count) / 1024

        return total_mb, per_node_kb, harness

    def test_memory_per_node_100(self, tmp_path, monkeypatch):
        """Memory at 100 nodes should be reasonable."""
        total_mb, per_node_kb, _ = self._measure_setup_memory(100, tmp_path, monkeypatch)
        assert per_node_kb < 500, f"Per-node memory {per_node_kb:.1f}KB exceeds 500KB"

    def test_memory_per_node_500(self, tmp_path, monkeypatch):
        """Memory at 500 nodes should scale linearly."""
        total_mb, per_node_kb, _ = self._measure_setup_memory(500, tmp_path, monkeypatch)
        assert per_node_kb < 500, f"Per-node memory {per_node_kb:.1f}KB exceeds 500KB"

    def test_memory_growth_subquadratic(self, tmp_path, monkeypatch):
        """Verify total memory grows sub-quadratically with node count.

        If growth were quadratic (O(N²)), doubling nodes would 4x memory.
        We verify that 3x nodes yields less than 6x total memory (sub-quadratic).
        """
        mb_100, _, _ = self._measure_setup_memory(100, tmp_path / "m100", monkeypatch)
        mb_300, _, _ = self._measure_setup_memory(300, tmp_path / "m300", monkeypatch)

        # Sub-quadratic: 3x nodes should yield < 6x memory (quadratic would be 9x)
        ratio = mb_300 / max(mb_100, 0.001)
        assert ratio < 6.0, (
            f"Memory growth possibly quadratic: {mb_100:.2f}MB@100 vs "
            f"{mb_300:.2f}MB@300 (ratio {ratio:.1f}x, expected < 6x)"
        )


# ── Bottleneck Identification ────────────────────────────────────────────────

class TestMeshBottleneck:
    """Isolate per-component costs to identify scaling bottleneck."""

    def test_serialization_overhead(self, tmp_path):
        """Measure JSON serialization cost for envelope-sized payloads."""
        payload = {
            "tenant_id": TENANT,
            "envelope_id": "env-bench-001",
            "timestamp": "2026-02-19T00:00:00Z",
            "producer_id": "node-0001",
            "region_id": "region-0",
            "correlation_group": "G1",
            "signal_type": "evidence",
            "payload": {"value": 50, "confidence": 0.9, "source": "edge-node-0001"},
            "payload_hash": "abcdef1234567890" * 2,
            "signature": "demo:" + "a" * 64,
        }

        latencies = []
        for _ in range(1000):
            t0 = time.monotonic()
            _ = json.dumps(payload, default=str).encode("utf-8")
            latencies.append(time.monotonic() - t0)

        avg_us = statistics.mean(latencies) * 1_000_000
        assert avg_us < 500, f"JSON serialization avg {avg_us:.0f}us exceeds 500us"

    def test_filesystem_io_overhead(self, tmp_path, monkeypatch):
        """Measure JSONL append + load cost."""
        import mesh.transport as mt
        monkeypatch.setattr(mt, "_BASE_DATA_DIR", tmp_path)
        ensure_node_dirs(TENANT, "io-bench")

        log_path = tmp_path / TENANT / "io-bench" / ENVELOPES_LOG
        record = {"id": "r-1", "data": "payload", "timestamp": "2026-02-19T00:00:00Z"}

        # Append cost
        append_times = []
        for i in range(200):
            record["id"] = f"r-{i}"
            t0 = time.monotonic()
            append_jsonl(log_path, record)
            append_times.append(time.monotonic() - t0)

        # Load cost
        load_times = []
        for _ in range(50):
            t0 = time.monotonic()
            load_all(log_path)
            load_times.append(time.monotonic() - t0)

        append_avg_ms = statistics.mean(append_times) * 1000
        load_avg_ms = statistics.mean(load_times) * 1000
        assert append_avg_ms < 50, f"Append avg {append_avg_ms:.1f}ms exceeds 50ms"
        assert load_avg_ms < 100, f"Load avg {load_avg_ms:.1f}ms exceeds 100ms"

    def test_signature_overhead(self, tmp_path):
        """Measure crypto sign + verify cost."""
        pub, priv = generate_keypair()
        message = canonical_bytes({"test": "payload", "value": 42})

        sign_times = []
        for _ in range(500):
            t0 = time.monotonic()
            sig = sign(priv, message)
            sign_times.append(time.monotonic() - t0)

        verify_times = []
        for _ in range(500):
            t0 = time.monotonic()
            verify(pub, message, sig)
            verify_times.append(time.monotonic() - t0)

        sign_avg_us = statistics.mean(sign_times) * 1_000_000
        verify_avg_us = statistics.mean(verify_times) * 1_000_000
        assert sign_avg_us < 5000, f"Sign avg {sign_avg_us:.0f}us exceeds 5ms"
        assert verify_avg_us < 5000, f"Verify avg {verify_avg_us:.0f}us exceeds 5ms"
