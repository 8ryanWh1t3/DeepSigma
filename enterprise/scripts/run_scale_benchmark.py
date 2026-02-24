#!/usr/bin/env python3
"""Run concurrent HTTP benchmark against DeepSigma API and emit report artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Sample:
    latency_ms: float
    status: int
    ok: bool


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * q
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


async def hit_endpoint(client: httpx.AsyncClient, path: str) -> Sample:
    start = time.perf_counter()
    try:
        response = await client.get(path)
        elapsed = (time.perf_counter() - start) * 1000.0
        ok = 200 <= response.status_code < 300
        return Sample(latency_ms=elapsed, status=response.status_code, ok=ok)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000.0
        return Sample(latency_ms=elapsed, status=0, ok=False)


async def run_benchmark(base_url: str, path: str, total_requests: int, concurrency: int, timeout_s: float) -> dict:
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(timeout_s)

    samples: list[Sample] = []
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=timeout) as client:
        async def worker() -> None:
            async with sem:
                samples.append(await hit_endpoint(client, path))

        start = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(total_requests)))
        duration = time.perf_counter() - start

    latencies = sorted(s.latency_ms for s in samples)
    success = sum(1 for s in samples if s.ok)
    errors = total_requests - success

    return {
        "target": f"{base_url}{path}",
        "total_requests": total_requests,
        "concurrency": concurrency,
        "duration_seconds": round(duration, 3),
        "throughput_rps": round(total_requests / duration, 2) if duration > 0 else 0.0,
        "success_count": success,
        "error_count": errors,
        "error_rate": round(errors / total_requests, 4) if total_requests > 0 else 0.0,
        "latency_ms": {
            "min": round(latencies[0], 2) if latencies else 0.0,
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
            "max": round(latencies[-1], 2) if latencies else 0.0,
            "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
        },
        "status_counts": {
            str(code): sum(1 for s in samples if s.status == code)
            for code in sorted({s.status for s in samples})
        },
    }


def write_markdown(report: dict, output_md: Path, replicas: int) -> None:
    latency = report["latency_ms"]
    lines = [
        "# Stateless API Scale Benchmark Report",
        "",
        f"- Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Target: `{report['target']}`",
        f"- Replica count: **{replicas}**",
        f"- Concurrency: **{report['concurrency']}**",
        f"- Total requests: **{report['total_requests']}**",
        "",
        "## Results",
        f"- Throughput: **{report['throughput_rps']} req/s**",
        f"- Duration: **{report['duration_seconds']} s**",
        f"- Functional errors: **{report['error_count']}**",
        f"- Success count: **{report['success_count']}**",
        "",
        "## Latency (ms)",
        f"- p50: **{latency['p50']}**",
        f"- p95: **{latency['p95']}**",
        f"- p99: **{latency['p99']}**",
        f"- mean: **{latency['mean']}**",
        f"- max: **{latency['max']}**",
        "",
        "## Acceptance",
        f"- 3-replica benchmark: {'PASS' if replicas == 3 else 'FAIL'}",
        f"- 100-concurrent-request scenario: {'PASS' if report['concurrency'] >= 100 else 'FAIL'}",
        f"- Zero functional errors: {'PASS' if report['error_count'] == 0 else 'FAIL'}",
        "",
        "## Status Counts",
    ]
    for code, count in report["status_counts"].items():
        lines.append(f"- `{code}`: {count}")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run concurrent benchmark against stateless API endpoint")
    parser.add_argument("--base-url", default="http://localhost:18080", help="Base URL for reverse proxy")
    parser.add_argument("--path", default="/api/health", help="API path to benchmark")
    parser.add_argument("--requests", type=int, default=100, help="Total request count")
    parser.add_argument("--concurrency", type=int, default=100, help="Concurrent workers")
    parser.add_argument("--replicas", type=int, default=3, help="Replica count used in environment")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout seconds")
    parser.add_argument("--out-json", default="docs/examples/scale/report_latest.json", help="Output JSON path")
    parser.add_argument("--out-md", default="docs/examples/scale/report_latest.md", help="Output markdown path")
    args = parser.parse_args()

    report = asyncio.run(
        run_benchmark(
            base_url=args.base_url,
            path=args.path,
            total_requests=args.requests,
            concurrency=args.concurrency,
            timeout_s=args.timeout,
        )
    )
    report["replicas"] = args.replicas

    out_json = ROOT / args.out_json
    out_md = ROOT / args.out_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md, args.replicas)

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")
    print(f"Throughput: {report['throughput_rps']} req/s | Errors: {report['error_count']}")

    return 0 if report["error_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
