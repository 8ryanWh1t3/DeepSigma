#!/usr/bin/env python3
"""Deterministic DISR re-encrypt benchmark with resource telemetry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepsigma.security.reencrypt import reencrypt_summary_to_dict, run_reencrypt_job  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rss_bytes(ru_maxrss: int) -> int:
    # Linux reports KB, macOS reports bytes.
    if sys.platform == "darwin":
        return int(ru_maxrss)
    return int(ru_maxrss * 1024)


def _write_dataset(path: Path, records: int, reset: bool) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if reset or not path.exists():
        with path.open("w", encoding="utf-8") as handle:
            for i in range(records):
                row = (
                    '{"tenant_id":"tenant-alpha","claim_id":"C-%06d","nonce":"NONCE-%06d",'
                    '"encrypted_payload":"PAYLOAD-%06d","key_id":"credibility","key_version":1,'
                    '"alg":"AES-256-GCM","aad":"tenant-alpha"}\n'
                ) % (i, i, i)
                handle.write(row)
    lines = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return lines, path.stat().st_size


def _scalability_score(mttr_seconds: float, records_per_second: float, mb_per_minute: float) -> float:
    score = 2.0  # baseline: benchmark evidence exists
    if mttr_seconds <= 300:
        score += 3
    elif mttr_seconds <= 600:
        score += 2
    elif mttr_seconds <= 1200:
        score += 1

    if records_per_second >= 5000:
        score += 3
    elif records_per_second >= 1000:
        score += 2
    elif records_per_second >= 100:
        score += 1

    if mb_per_minute >= 500:
        score += 2
    elif mb_per_minute >= 100:
        score += 1
    return max(0.0, min(10.0, score))


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark DISR re-encrypt dry-run with telemetry")
    parser.add_argument("--records", type=int, default=100000, help="Number of records to benchmark")
    parser.add_argument(
        "--dataset-dir",
        default="artifacts/benchmarks/reencrypt",
        help="Directory for generated benchmark dataset",
    )
    parser.add_argument(
        "--checkpoint",
        default="artifacts/benchmarks/reencrypt/reencrypt_checkpoint.json",
        help="Checkpoint path for the benchmark run",
    )
    parser.add_argument(
        "--metrics-out",
        default="release_kpis/scalability_metrics.json",
        help="Path to write benchmark metrics JSON",
    )
    parser.add_argument(
        "--summary-out",
        default="artifacts/benchmarks/reencrypt/benchmark_summary.json",
        help="Path to write benchmark summary JSON",
    )
    parser.add_argument("--reset-dataset", action="store_true", help="Regenerate dataset from scratch")
    parser.add_argument(
        "--real-workload",
        action="store_true",
        help="Run real re-encrypt workload (requires DEEPSIGMA_MASTER_KEY and DEEPSIGMA_PREVIOUS_MASTER_KEY)",
    )
    args = parser.parse_args()

    dataset_dir = (ROOT / args.dataset_dir).resolve()
    claims_path = dataset_dir / "claims.jsonl"
    records_targeted, bytes_targeted = _write_dataset(claims_path, args.records, args.reset_dataset)

    started_at = _utc_now_iso()
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)

    summary = run_reencrypt_job(
        tenant_id="tenant-alpha",
        dry_run=not args.real_workload,
        resume=False,
        data_dir=dataset_dir,
        checkpoint_path=(ROOT / args.checkpoint).resolve(),
        actor_user="benchmark-runner",
        actor_role="coherence_steward",
    )

    wall_elapsed = max(time.perf_counter() - wall_start, 0.001)
    cpu_elapsed = max(time.process_time() - cpu_start, 0.0)
    ru_end = resource.getrusage(resource.RUSAGE_SELF)
    rss_peak_bytes = max(_rss_bytes(ru_start.ru_maxrss), _rss_bytes(ru_end.ru_maxrss))
    ended_at = _utc_now_iso()

    records_per_second = records_targeted / wall_elapsed
    mb_per_minute = (bytes_targeted / (1024 * 1024)) / (wall_elapsed / 60.0)
    score = _scalability_score(wall_elapsed, records_per_second, mb_per_minute)

    metrics = {
        "schema_version": "1.0",
        "metric_family": "disr_scalability",
        "execution_mode": "real_workload" if args.real_workload else "dry_run",
        "evidence_level": "real_workload" if args.real_workload else "simulated",
        "kpi_eligible": bool(args.real_workload),
        "run_started_at": started_at,
        "run_completed_at": ended_at,
        "records_targeted": records_targeted,
        "bytes_targeted": bytes_targeted,
        "wall_clock_seconds": round(wall_elapsed, 6),
        "cpu_seconds": round(cpu_elapsed, 6),
        "rss_peak_bytes": rss_peak_bytes,
        "throughput_records_per_second": round(records_per_second, 3),
        "throughput_mb_per_minute": round(mb_per_minute, 6),
        "scalability_score": round(score, 2),
        "dataset_sha256": hashlib.sha256(claims_path.read_bytes()).hexdigest(),
        "deterministic_seed": "DISR-BENCH-2026",
    }

    metrics_out = (ROOT / args.metrics_out).resolve()
    metrics_out.parent.mkdir(parents=True, exist_ok=True)
    metrics_out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    output = {
        "metrics": metrics,
        "reencrypt_summary": reencrypt_summary_to_dict(summary),
        "dataset_path": str(claims_path),
    }
    summary_out = (ROOT / args.summary_out).resolve()
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(output, indent=2))
    print(f"Wrote: {metrics_out}")
    print(f"Wrote: {summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
