# DISR 10-Minute Demo

This demo proves the DISR loop in one pass:

1. Detectable: run the crypto misuse gate.
2. Rotatable: rotate keys with explicit DRI approval context.
3. Recoverable: run a re-encrypt dry-run and checkpoint result.

## Prerequisites

- Python environment with DeepSigma dependencies installed.
- Optional signing key in env:
  - `export DEEPSIGMA_AUTHORITY_SIGNING_KEY="demo-signing-key"`

## Honesty flags (important)

- `make security-demo` and default `make reencrypt-benchmark` are **dry-run/simulated** workflows.
- These flows measure orchestration + IO behavior, not production-grade cryptographic throughput.
- KPI uplift from these artifacts is capped unless metrics are marked `kpi_eligible=true` from real workload runs.
- If `DEEPSIGMA_AUTHORITY_SIGNING_KEY` is unset, demo signing uses a placeholder default key.

## Commands

```bash
make security-gate
make security-demo
make reencrypt-benchmark
```

## Expected outputs

`make security-gate` writes:

- `release_kpis/SECURITY_GATE_REPORT.md`
- `release_kpis/SECURITY_GATE_REPORT.json`

`make security-demo` writes:

- `artifacts/disr_demo/keyring.json`
- `artifacts/disr_demo/key_rotation_events.jsonl`
- `artifacts/disr_demo/authority_ledger.json`
- `artifacts/disr_demo/reencrypt_checkpoint.json`
- `artifacts/disr_demo/disr_demo_summary.json`
- `release_kpis/security_metrics.json`

`make reencrypt-benchmark` writes:

- `release_kpis/scalability_metrics.json`
- `artifacts/benchmarks/reencrypt/benchmark_summary.json`
- `artifacts/benchmarks/reencrypt/claims.jsonl` (100k-record deterministic fixture by default)

To run a real workload benchmark (not dry-run), use:

```bash
make reencrypt-benchmark ARGS="--real-workload"
```

## What to verify

- Rotation event exists with `event_type = KEY_ROTATED`.
- Security event stream includes signed `AUTHORIZED_KEY_ROTATION`.
- Authority ledger contains an `AUTHORIZED_KEY_ROTATION` entry.
- Re-encrypt result is `dry_run` with deterministic checkpoint output.
- Metrics file contains numeric MTTR and throughput values.

## Metrics (Economic Measurability)

`release_kpis/security_metrics.json` captures:

- `mttr_seconds`
- `reencrypt_records_per_second`
- `reencrypt_mb_per_minute`
- `execution_mode`, `evidence_level`, `kpi_eligible`
- `signing_key_source` and `signing_notice`

`release_kpis/scalability_metrics.json` captures:

- `wall_clock_seconds`
- `cpu_seconds`
- `rss_peak_bytes`
- `throughput_records_per_second`
- `throughput_mb_per_minute`
- `execution_mode`, `evidence_level`, `kpi_eligible`
