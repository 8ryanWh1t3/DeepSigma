# DISR 10-Minute Demo

This demo proves the DISR loop in one pass:

1. Detectable: run the crypto misuse gate.
2. Rotatable: rotate keys with explicit DRI approval context.
3. Recoverable: run a re-encrypt dry-run and checkpoint result.

## Prerequisites

- Python environment with DeepSigma dependencies installed.
- Optional signing key in env:
  - `export DEEPSIGMA_AUTHORITY_SIGNING_KEY="demo-signing-key"`

## Commands

```bash
make security-gate
make security-demo
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

## What to verify

- Rotation event exists with `event_type = KEY_ROTATED`.
- Security event stream includes signed `AUTHORIZED_KEY_ROTATION`.
- Authority ledger contains an `AUTHORIZED_KEY_ROTATION` entry.
- Re-encrypt result is `dry_run` with deterministic checkpoint output.
